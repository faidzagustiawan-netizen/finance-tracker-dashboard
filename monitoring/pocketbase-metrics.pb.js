/// <reference path="../pb_data/types.d.ts" />
//
// Prometheus metrics for PocketBase.
//
// PocketBase 0.22 has no /metrics endpoint, yet Prometheus was configured to
// scrape one, so the target sat permanently DOWN and the PocketBaseDown alert
// fired continuously -- a false alarm, since the service was healthy the whole
// time. This hook exposes a real text-format endpoint so `up` means what it says.
//
// Counts come from a single query per collection. Values change only when the
// data does, which keeps the series stable for alerting.

routerAdd("GET", "/metrics", (c) => {
    // Escape a value for inclusion in a Prometheus label.
    const label = (v) => String(v).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, " ");

    const lines = [];
    const add = (name, help, value) => {
        lines.push("# HELP " + name + " " + help);
        lines.push("# TYPE " + name + " gauge");
        lines.push(name + " " + value);
    };

    try {
        // findCollectionsByType("base") is the 0.22 way to list user collections;
        // the admin/system ones are not interesting to monitor.
        const collections = $app.dao().findCollectionsByType("base");

        add("pocketbase_collections_total", "Number of base collections.", collections.length);

        lines.push("# HELP pocketbase_records Collection record counts.");
        lines.push("# TYPE pocketbase_records gauge");

        let totalRecords = 0;
        for (const col of collections) {
            if (!col) continue;
            let n = 0;
            try {
                n = $app.dao().recordQuery(col).count();
            } catch (e) {
                // A collection that cannot be counted must not fail the scrape.
                continue;
            }
            totalRecords += n;
            lines.push('pocketbase_records{collection="' + label(col.name) + '"} ' + n);
        }

        add("pocketbase_records_total", "Total records across base collections.", totalRecords);
        add("pocketbase_up", "Whether this endpoint could gather statistics.", 1);
    } catch (err) {
        lines.length = 0;
        add("pocketbase_up", "Whether this endpoint could gather statistics.", 0);
        lines.push("# HELP pocketbase_metrics_error Metrics collection failure.");
        lines.push("# TYPE pocketbase_metrics_error gauge");
        lines.push('pocketbase_metrics_error{error="' + label(err) + '"} 1');
    }

    return c.string(200, lines.join("\n") + "\n");
});
