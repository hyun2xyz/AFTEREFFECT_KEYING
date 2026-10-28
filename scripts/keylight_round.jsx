/* One Keylight tuning round on the comp that ae_comp.py keylight built.
 * keylight.py fills in the job. The script changes only the listed effect parameters (and the
 * garbage matte when asked), renders check frames with comp.saveFrameToPng, puts every view and
 * layer switch back, and writes a JSON receipt next to itself. It never saves, closes or renders
 * through the render queue. Run it with File > Scripts > Run Script File or keylight.py run. */
(function () {
    var job = /*__ROUND_JOB__*/;
    var report = {schema: "keylight-round.v1", job_id: job.job_id, round: job.round, status: "failed",
                  ae_version: app.version, effects: [], files: [], missing: [], error: null};

    function encode(v) {
        var parts = [], k;
        if (v === null || v === undefined) return "null";
        if (typeof v === "string") return '"' + v.replace(/[\\"\x00-\x1f\u2028\u2029]/g, function (c) {
            return "\\u" + ("0000" + c.charCodeAt(0).toString(16)).slice(-4);
        }) + '"';
        if (typeof v === "number") return isFinite(v) ? String(v) : "null";
        if (typeof v === "boolean") return String(v);
        if (v instanceof Array) {
            for (k = 0; k < v.length; k++) parts.push(encode(v[k]));
            return "[" + parts.join(",") + "]";
        }
        for (k in v) if (v.hasOwnProperty(k)) parts.push(encode(k) + ":" + encode(v[k]));
        return "{" + parts.join(",") + "}";
    }
    function fail(message) { throw new Error(message); }
    function pad(n) { return ("0000" + n).slice(-4); }

    function findComp(name) {
        var found = null;
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && item.name === name) {
                if (found) fail("Two comps are named " + name);
                found = item;
            }
        }
        if (!found) fail("Comp not found: " + name + ". Build it with ae_comp.py keylight first.");
        return found;
    }
    function effect(layer, name) {
        var fx = layer.property("ADBE Effect Parade").property(name);
        if (!fx) fail("Effect not found on " + layer.name + ": " + name);
        return fx;
    }
    function setGarbage(comp, points) {
        var matte = comp.layer("Garbage Matte");
        if (!matte) fail("No Garbage Matte layer; rebuild the comp with a keylight.garbage polygon in shot.json");
        var path = matte.property("ADBE Root Vectors Group").property(1).property("ADBE Vectors Group").property(1);
        var shape = new Shape();
        shape.vertices = points;
        shape.closed = true;
        path.property("ADBE Vector Shape").setValue(shape);
    }
    function readEffects(layer) {
        var out = [];
        for (var i = 0; i < job.read.length; i++) {
            var spec = job.read[i], fx = effect(layer, spec.name), values = {};
            for (var key in spec.params) if (spec.params.hasOwnProperty(key)) values[key] = fx.property(spec.params[key]).value;
            out.push({name: spec.name, enabled: fx.enabled, params: values});
        }
        return out;
    }

    app.beginUndoGroup("Keylight round " + job.round);
    try {
        var comp = findComp(job.comp_name), layer = comp.layer(job.layer);
        if (!layer) fail("Layer not found: " + job.layer);
        var background = job.background ? comp.layer(job.background) : null;
        if (job.garbage) setGarbage(comp, job.garbage);
        for (var c = 0; c < job.changes.length; c++) {
            var change = job.changes[c], fx = effect(layer, change.effect);
            for (var key in change.params) if (change.params.hasOwnProperty(key)) fx.property(key).setValue(change.params[key]);
            if (change.enabled !== null) fx.enabled = change.enabled;
        }
        report.effects = readEffects(layer);

        // Every saveFrameToPng call renders the comp as it is at that moment; the files land later.
        var edge = effect(layer, "Keylight Edge"), core = effect(layer, "Keylight Core");
        var edgeView = edge.property(job.match.view), coreView = core.property(job.match.view);
        var backgroundWas = background ? background.enabled : null, edgeWas = edge.enabled;
        for (var f = 0; f < job.frames.length; f++) {
            for (var v = 0; v < job.views.length; v++) {
                var view = job.views[v];
                if (view.name === "core" && !core.enabled) continue;
                if (view.name === "core") {
                    edge.enabled = false;
                    coreView.setValue(view.core_view);
                } else {
                    edgeView.setValue(view.edge_view);
                }
                if (background) background.enabled = view.background;
                var file = new File(job.out_dir + "/" + view.name + "_" + pad(job.frames[f]) + ".png");
                if (file.exists) file.remove();
                comp.saveFrameToPng(job.frames[f] / job.fps, file);
                report.files.push(file.fsName);
                if (view.name === "core") {
                    edge.enabled = edgeWas;
                    coreView.setValue(job.core_view_normal);
                }
            }
        }
        edgeView.setValue(job.edge_view_normal);
        if (background) background.enabled = backgroundWas;

        var deadline = new Date().getTime() + job.wait_ms;
        for (;;) {
            report.missing = [];
            for (var m = 0; m < report.files.length; m++) if (!new File(report.files[m]).exists) report.missing.push(report.files[m]);
            if (!report.missing.length || new Date().getTime() > deadline) break;
            $.sleep(250);
        }
        if (report.missing.length) fail(report.missing.length + " check frames were not written in time");
        report.status = "ok";
    } catch (error) {
        report.error = error.toString();
    } finally {
        app.endUndoGroup();
    }

    var receipt = new File(job.receipt);
    receipt.encoding = "UTF-8";
    if (receipt.open("w")) {
        receipt.write(encode(report));
        receipt.close();
    }
    return encode(report);
})();
