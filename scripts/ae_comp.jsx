/* After Effects comp for one shot: the original plate and result layers in a new, empty project.
 * scripts/ae_comp.py fills in the job; the student runs the generated file with
 * File > Scripts > Run Script File. It adds one folder, the footage and one comp.
 * It does not save, close, render or touch a project that already has items.
 * On failure it removes what this run added and restores the project settings. */
(function () {
    var job = /*__COMP_JOB__*/;
    var project = app.project, created = [], previous = null;
    var report = {schema: "ae-comp.v1", job_id: job.job_id, shot: job.shot, status: "failed",
                  ae_version: app.version, project: null, comp: null, layers: [], error: null};

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
    function frames(seconds) { return Math.round(seconds * job.fps); }
    function hasProfile(name) {
        var names = project.listColorProfiles();
        for (var i = 0; i < names.length; i++) if (names[i] === name) return true;
        return false;
    }
    function alphaName(source) {
        if (!source.hasAlpha || source.alphaMode === AlphaMode.IGNORE) return "ignore";
        return source.alphaMode === AlphaMode.STRAIGHT ? "straight" : "premultiplied";
    }

    function setProject() {
        var wanted = job.project;
        previous = {bpc: project.bitsPerChannel, working_space: project.workingSpace, linear: project.linearBlending};
        project.bitsPerChannel = wanted.bits_per_channel;
        if (wanted.working_space) {
            // A working space profile only applies with Adobe color management (0); OCIO is 1.
            if (project.colorManagementSystem !== undefined && project.colorManagementSystem !== 0)
                fail(job.messages.not_adobe_color);
            if (!hasProfile(wanted.working_space)) fail("Working space not available: " + wanted.working_space);
            project.workingSpace = wanted.working_space;
        }
        if (wanted.linear_blending !== null) project.linearBlending = wanted.linear_blending;
    }

    function importFootage(spec, folder) {
        var file = new File(spec.path);
        if (!file.exists) fail("Missing " + spec.name + ": " + spec.path);
        var options = new ImportOptions(file);
        if (spec.kind === "sequence") { options.sequence = true; options.forceAlphabetical = true; }
        var item = project.importFile(options);
        created.push(item);
        item.parentFolder = folder;
        var source = item.mainSource;
        if (spec.kind === "sequence") {
            source.conformFrameRate = job.fps;
            if (frames(item.duration) !== spec.frames)
                fail(spec.name + " imported as " + frames(item.duration) + " frames, expected " + spec.frames);
        }
        if (spec.alpha === "straight") {
            if (!source.hasAlpha) fail(spec.name + " has no alpha channel: " + spec.path);
            source.alphaMode = AlphaMode.STRAIGHT;
        } else if (source.hasAlpha) {
            source.alphaMode = AlphaMode.IGNORE;
        }
        if (spec.pixel_aspect) item.pixelAspect = spec.pixel_aspect;
        return item;
    }

    function build() {
        if (project.numItems !== 0) fail(job.messages.not_empty);
        setProject();
        var folder = project.items.addFolder(job.folder_name);
        created.push(folder);
        var items = [], i;
        for (i = 0; i < job.layers.length; i++) items.push(importFootage(job.layers[i], folder));
        var plate = items[0];
        for (i = 1; i < items.length; i++) {
            if (job.layers[i].from_plate && (items[i].width !== plate.width || items[i].height !== plate.height))
                fail(job.layers[i].name + " is " + items[i].width + "x" + items[i].height +
                     ", plate is " + plate.width + "x" + plate.height);
        }
        var comp = project.items.addComp(job.comp_name, plate.width, plate.height, plate.pixelAspect,
                                         job.layers[0].frames / job.fps, job.fps);
        created.push(comp);
        comp.parentFolder = folder;
        // job.layers runs bottom to top; each add() lands above the previous layer.
        for (i = 0; i < job.layers.length; i++) {
            var spec = job.layers[i], layer = comp.layers.add(items[i]);
            layer.name = spec.name;
            if (spec.kind === "still") {
                layer.startTime = 0;
                layer.outPoint = comp.duration;
            } else {
                layer.startTime = spec.start_frame / job.fps;
            }
            layer.enabled = spec.enabled;
        }
        return comp;
    }

    function readback(comp) {
        report.project = {bits_per_channel: project.bitsPerChannel, working_space: project.workingSpace,
                          linear_blending: project.linearBlending};
        report.comp = {name: comp.name, width: comp.width, height: comp.height, pixel_aspect: comp.pixelAspect,
                       fps: comp.frameRate, frames: frames(comp.duration)};
        for (var i = comp.numLayers; i >= 1; i--) {
            var layer = comp.layer(i), item = layer.source, source = item.mainSource;
            report.layers.push({name: layer.name, enabled: layer.enabled, in_frame: frames(layer.inPoint),
                                out_frame: frames(layer.outPoint), source: source.file.fsName,
                                alpha: alphaName(source), width: item.width, height: item.height,
                                pixel_aspect: item.pixelAspect, frames: source.isStill ? 1 : frames(item.duration)});
        }
    }

    function undo() {
        for (var i = created.length - 1; i >= 0; i--) { try { created[i].remove(); } catch (ignored) {} }
        if (!previous) return;
        try { project.bitsPerChannel = previous.bpc; } catch (ignored) {}
        // workingSpace reads "None" when unset, but writing "None" raises a warning dialog; "" clears it.
        try { project.workingSpace = previous.working_space === "None" ? "" : previous.working_space; } catch (ignored) {}
        try { project.linearBlending = previous.linear; } catch (ignored) {}
    }

    app.beginUndoGroup("Build " + job.comp_name);
    try {
        var comp = build();
        readback(comp);
        report.status = "ok";
        comp.openInViewer();
    } catch (error) {
        report.error = error.toString();
        undo();
    } finally {
        app.endUndoGroup();
    }

    // Writing files needs Preferences > Scripting & Expressions > Allow Scripts to Write Files
    // and Access Network. Read it (never change it) so a missing permission skips the receipt
    // instead of raising AE's error dialog.
    var receipt = new File(job.receipt), recorded = false, allowed = true;
    try { allowed = app.preferences.getPrefAsLong("Main Pref Section v2", "Pref_SCRIPTING_FILE_NETWORK_SECURITY") === 1; }
    catch (ignored) {}
    receipt.encoding = "UTF-8";
    if (allowed && receipt.open("w")) {
        recorded = receipt.write(encode(report));
        receipt.close();
    }
    if (job.dialogs) {
        var text = report.status === "ok" ? job.messages.done : job.messages.failed + "\n" + report.error;
        alert(recorded ? text : text + "\n\n" + job.messages.no_receipt);
    }
    return encode(report);
})();
