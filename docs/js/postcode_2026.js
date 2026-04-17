import * as duckdb from 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.33.1-dev45.0/+esm';

// --- Postcode utilities ---

const POSTCODE_REGEX = /^(?:[A-Z]{2}[0-9][A-Z]|[A-Z][0-9][A-Z]|[A-Z][0-9]|[A-Z][0-9]{2}|[A-Z]{2}[0-9]|[A-Z]{2}[0-9]{2})[0-9][A-Z]{2}$/;

function normalise(postcode) {
    return postcode.replace(/\s/g, "").toUpperCase();
}

function postcodeToInt(postcode) {
    return parseInt(normalise(postcode), 36);
}

function isValidPostcode(postcode) {
    return POSTCODE_REGEX.test(normalise(postcode));
}

/**
 * Parse raw input lines into an array of { index, valid, intVal } entries.
 */
function parsePostcodeLines(lines) {
    return lines.map((line, i) => {
        const cleaned = line.trim();
        if (!cleaned || !isValidPostcode(cleaned)) {
            return { index: i, valid: false, intVal: null };
        }
        return { index: i, valid: true, intVal: postcodeToInt(cleaned) };
    });
}

// --- DuckDB setup ---

const PARQUET_PATH = 'js_data/postcode_lookup_int.parquet';

async function initDuckDB() {
    const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
    const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

    // Start parquet fetch in parallel with DuckDB WASM instantiation
    const parquetUrl = new URL(PARQUET_PATH, window.location.href).href;
    const parquetPromise = fetch(parquetUrl)
        .then(r => r.arrayBuffer())
        .then(buf => new Uint8Array(buf));

    const workerUrl = URL.createObjectURL(
        new Blob([`importScripts("${bundle.mainWorker}");`], { type: 'text/javascript' })
    );
    const worker = new Worker(workerUrl);
    const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
    URL.revokeObjectURL(workerUrl);

    const parquetBuffer = await parquetPromise;
    await db.registerFileBuffer('postcode_lookup.parquet', parquetBuffer);

    const conn = await db.connect();
    await conn.query(`CREATE TABLE lookup AS SELECT * FROM 'postcode_lookup.parquet'`);

    return conn;
}

// --- Query logic ---

const BATCH_SIZE = 1000;

/**
 * Query the lookup table for the given entries, returning a Map of
 * row index -> result value.
 */
async function queryLookup(conn, validEntries, outputColumn) {
    let result;

    if (validEntries.length <= BATCH_SIZE) {
        // Small input: inline VALUES avoids temp table overhead
        const valuesList = validEntries.map(e => `(${e.index}, ${e.intVal})`).join(", ");
        result = await conn.query(`
            SELECT u.row_idx, l.${outputColumn} as result
            FROM (VALUES ${valuesList}) AS u(row_idx, postcode_int)
            LEFT JOIN lookup l ON u.postcode_int = l.postcode_int
            ORDER BY u.row_idx
        `);
    } else {
        // Large input: batched inserts into a temp table
        await conn.query(`DROP TABLE IF EXISTS user_postcodes`);
        await conn.query(`CREATE TEMP TABLE user_postcodes (row_idx INTEGER, postcode_int BIGINT)`);

        for (let i = 0; i < validEntries.length; i += BATCH_SIZE) {
            const batch = validEntries.slice(i, i + BATCH_SIZE);
            const valuesList = batch.map(e => `(${e.index}, ${e.intVal})`).join(", ");
            await conn.query(`INSERT INTO user_postcodes VALUES ${valuesList}`);
        }

        result = await conn.query(`
            SELECT u.row_idx, l.${outputColumn} as result
            FROM user_postcodes u
            LEFT JOIN lookup l ON u.postcode_int = l.postcode_int
            ORDER BY u.row_idx
        `);
    }

    const resultMap = new Map();
    for (const row of result.toArray()) {
        resultMap.set(Number(row.row_idx), row.result);
    }
    return resultMap;
}

/**
 * Build the output lines from parsed entries and query results.
 * Inserts a header label if the first line looks like a column header.
 */
function buildOutput(entries, resultMap, outputColumn) {
    const output = entries.map(e => {
        if (!e.valid) return "";
        const val = resultMap.get(e.index);
        return val != null ? String(val) : "";
    });

    const firstLineIsHeader = !entries[0].valid && entries.length > 1;
    if (firstLineIsHeader) {
        output[0] = outputColumn;
    }

    return output;
}

// --- Analytics ---

function logCount(numPostcodes) {
    if (typeof gtag !== "undefined") {
        gtag("event", "postcode_tool_2026", {
            "postcode_count": numPostcodes
        });
    }
}

// --- UI wiring ---

const DEBOUNCE_MS = 10;

function setupUI(conn) {
    const postcodesEl = document.getElementById("postcodes");
    const constituenciesEl = document.getElementById("constituencies");
    const copyButton = document.getElementById("copyButton");
    const statusEl = document.getElementById("status");

    statusEl.textContent = "Ready! Paste postcodes in the box below.";
    postcodesEl.disabled = false;

    function resetCopyButton() {
        copyButton.classList.remove("btn-success");
        copyButton.classList.add("btn-primary");
        copyButton.textContent = "Copy results to clipboard";
    }

    async function process() {
        const outputColumn = document.querySelector('input[name="output_type"]:checked').value;
        const rawLines = postcodesEl.value.split("\n");

        if (!rawLines.length || (rawLines.length === 1 && rawLines[0].trim() === "")) {
            constituenciesEl.value = "";
            return;
        }

        resetCopyButton();

        const entries = parsePostcodeLines(rawLines);
        const validEntries = entries.filter(e => e.valid);

        if (validEntries.length === 0) {
            const output = buildOutput(entries, new Map(), outputColumn);
            constituenciesEl.value = output.join("\n");
            return;
        }

        try {
            const resultMap = await queryLookup(conn, validEntries, outputColumn);
            const output = buildOutput(entries, resultMap, outputColumn);
            constituenciesEl.value = output.join("\n");
            logCount(rawLines.length);
        } catch (err) {
            console.error("Query error:", err);
            constituenciesEl.value = "Error processing postcodes. See console for details.";
        }
    }

    let debounceTimer = null;
    function debouncedProcess() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(process, DEBOUNCE_MS);
    }

    postcodesEl.addEventListener("input", debouncedProcess);
    document.getElementsByName("output_type").forEach(el => {
        el.addEventListener("input", debouncedProcess);
    });

    copyButton.addEventListener("click", () => {
        navigator.clipboard.writeText(constituenciesEl.value)
            .then(() => {
                copyButton.classList.remove("btn-primary");
                copyButton.classList.add("btn-success");
                copyButton.textContent = "Copied to clipboard";
            })
            .catch(err => console.error("Error copying to clipboard:", err));
    });
}

// --- Entrypoint ---

initDuckDB()
    .then(conn => setupUI(conn))
    .catch(err => {
        console.error("Failed to initialize DuckDB:", err);
        document.getElementById("status").textContent = "Failed to load. Please refresh the page.";
    });
