function normalizePercentages(count, spec) {
    const cleaned = (spec || "").split(":");
    const entries = [];
    let fixedTotal = 0;
    let starCount = 0;

    for (let i = 0; i < count; ++i) {
        const token = (cleaned[i] || "").trim();
        if (token === "" || token === "*") {
            entries.push({ type: "star" });
            starCount += 1;
            continue;
        }

        const numeric = parseFloat(token.replace("%", ""));
        if (isNaN(numeric)) {
            entries.push({ type: "star" });
            starCount += 1;
            continue;
        }

        entries.push({ type: "fixed", value: numeric });
        fixedTotal += numeric;
    }

    const result = new Array(count);
    let leftover = 100 - fixedTotal;

    if (leftover < 0) {
        leftover = 0;
    }

    let starValue = 0;
    if (starCount > 0) {
        starValue = leftover > 0 ? leftover / starCount : (count > 0 ? 100 / count : 0);
    }

    for (let i = 0; i < count; ++i) {
        const entry = entries[i];
        result[i] = entry && entry.type === "fixed" ? entry.value : starValue;
    }

    let total = 0;
    for (let i = 0; i < count; ++i) {
        total += result[i];
    }

    if (total === 0) {
        const fallback = count > 0 ? 100 / count : 0;
        for (let i = 0; i < count; ++i) {
            result[i] = fallback;
        }
        return result;
    }

    for (let i = 0; i < count; ++i) {
        result[i] = result[i] * 100 / total;
    }

    return result;
}

function parseLayout(definition) {
    if (!definition || typeof definition !== "string") {
        return { columns: [], areaCount: 0 };
    }

    const segments = definition.split("/");
    if (segments.length === 0) {
        return { columns: [], areaCount: 0 };
    }

    const headerMatch = segments[0].match(/^(\d+)\s*S\|(.+)$/i);
    if (!headerMatch) {
        return { columns: [], areaCount: 0 };
    }

    const columnsRequested = parseInt(headerMatch[1], 10);
    const columnWidths = normalizePercentages(columnsRequested, headerMatch[2]);

    const columns = [];
    let runningIndex = 0;

    for (let c = 0; c < columnsRequested; ++c) {
        const segment = segments[c + 1] || "";
        const rowsMatch = segment.match(/^(\d+)\s*R\|?(.*)$/i);
        const rowsRequested = rowsMatch ? parseInt(rowsMatch[1], 10) : 1;
        const rowSpec = rowsMatch ? rowsMatch[2] : "";
        const rowHeights = normalizePercentages(rowsRequested, rowSpec);
        const rows = [];

        for (let r = 0; r < rowsRequested; ++r) {
            rows.push({
                heightPercent: rowHeights[r],
                areaIndex: runningIndex + r
            });
        }

        columns.push({
            widthPercent: columnWidths[c],
            rows: rows,
            startIndex: runningIndex
        });

        runningIndex += rowsRequested;
    }

    return {
        columns: columns,
        areaCount: runningIndex
    };
}

function layoutSummary(definition) {
    const result = parseLayout(definition);
    return {
        columnCount: result.columns.length,
        areaCount: result.areaCount
    };
}

export { parseLayout, layoutSummary };
