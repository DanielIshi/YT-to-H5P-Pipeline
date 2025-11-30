<?php
define('CLI_SCRIPT', true);
require('/bitnami/moodle/config.php');
require_once($CFG->libdir . '/filelib.php');

use core_h5p\factory;
use core_h5p\helper;
use core_h5p\core;

$CFG->debug = E_ALL;
$CFG->debugdisplay = 1;
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Hole die neueste H5P Datei
$sql = "SELECT f.pathnamehash, f.filename, f.contextid, f.contenthash, ctx.instanceid as cmid
         FROM {files} f
         JOIN {context} ctx ON ctx.id = f.contextid
         WHERE f.component = 'mod_h5pactivity'
         AND f.filearea = 'package'
         AND f.filename != '.'
         ORDER BY f.id DESC
         LIMIT 1";

$fileinfo = $DB->get_record_sql($sql);
echo "Processing: " . $fileinfo->filename . "\n";
echo "Context ID: " . $fileinfo->contextid . "\n";
echo "Content hash: " . $fileinfo->contenthash . "\n";

$fs = get_file_storage();
$storedfile = $fs->get_file_by_hash($fileinfo->pathnamehash);

// Config
$config = new stdClass();
$config->frame = 1;
$config->export = 0;
$config->embed = 0;
$config->copyright = 0;

echo "\n=== CALLING helper::save_h5p ===\n";

try {
    // helper::save_h5p ist die offizielle API
    $factory = new factory();

    // Debug: Was macht save_h5p intern?
    // Es validiert das Paket und speichert den Inhalt
    // Parameter: factory, stored_file, config, skip_content_check, disable_file_check

    $h5pid = helper::save_h5p($factory, $storedfile, $config, false, false);

    if ($h5pid !== false) {
        echo "SUCCESS! H5P ID: " . $h5pid . "\n";

        // Prüfe den erstellten Content
        $h5p = $DB->get_record('h5p', ['id' => $h5pid]);
        if ($h5p) {
            echo "JSON Content length: " . strlen($h5p->jsoncontent) . "\n";
            echo "Main library ID: " . $h5p->mainlibraryid . "\n";
        }
    } else {
        echo "FAILED - save_h5p returned false\n";

        // Hole Fehler aus dem Framework
        $interface = $factory->get_framework();
        $errors = $interface->getMessages('error');
        if (!empty($errors)) {
            echo "\nErrors from framework:\n";
            foreach($errors as $msg) {
                echo "  - " . $msg . "\n";
            }
        }

        // Prüfe auch info messages
        $infos = $interface->getMessages('info');
        if (!empty($infos)) {
            echo "\nInfo messages:\n";
            foreach($infos as $msg) {
                echo "  - " . $msg . "\n";
            }
        }
    }

} catch (Throwable $e) {
    echo "Exception: " . $e->getMessage() . "\n";
    echo "File: " . $e->getFile() . ":" . $e->getLine() . "\n";
}

// Zeige H5P-Tabellen-Status
echo "\n=== DATABASE STATUS ===\n";
echo "h5p entries: " . $DB->count_records('h5p') . "\n";
echo "h5p_libraries: " . $DB->count_records('h5p_libraries') . "\n";

// Zeige vorhandene h5p entries
$entries = $DB->get_records('h5p', null, 'id DESC', 'id, pathnamehash, mainlibraryid', 0, 5);
echo "\nRecent h5p entries:\n";
foreach ($entries as $entry) {
    echo "  ID " . $entry->id . ": lib=" . $entry->mainlibraryid . ", hash=" . substr($entry->pathnamehash, 0, 20) . "...\n";
}

// Zeige MultiChoice Library
echo "\nMultiChoice library:\n";
$mc = $DB->get_record_sql("SELECT * FROM {h5p_libraries} WHERE machinename = 'H5P.MultiChoice' ORDER BY majorversion DESC, minorversion DESC LIMIT 1");
if ($mc) {
    echo "  ID: " . $mc->id . "\n";
    echo "  Version: " . $mc->majorversion . "." . $mc->minorversion . "." . $mc->patchversion . "\n";
    echo "  Runnable: " . $mc->runnable . "\n";
}
