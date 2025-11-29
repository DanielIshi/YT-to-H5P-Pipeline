<?php
define('CLI_SCRIPT', true);
require('/bitnami/moodle/config.php');
require_once($CFG->libdir . '/filelib.php');

use core_h5p\factory;
use core_h5p\helper;

$CFG->debug = E_ALL;
$CFG->debugdisplay = 1;
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Hole die neueste H5P Datei
$sql = "SELECT f.pathnamehash, f.filename, f.contextid, f.contenthash
         FROM {files} f
         JOIN {context} ctx ON ctx.id = f.contextid
         WHERE f.component = 'mod_h5pactivity'
         AND f.filearea = 'package'
         AND f.filename != '.'
         ORDER BY f.id DESC
         LIMIT 1";

$fileinfo = $DB->get_record_sql($sql);
echo "Processing: " . $fileinfo->filename . "\n";
echo "Pathname hash: " . $fileinfo->pathnamehash . "\n";

$fs = get_file_storage();
$storedfile = $fs->get_file_by_hash($fileinfo->pathnamehash);

// Config
$config = new stdClass();
$config->frame = 1;
$config->export = 0;
$config->embed = 0;
$config->copyright = 0;

echo "\n=== CALLING helper::save_h5p ===\n";

$factory = new factory();
$h5pid = helper::save_h5p($factory, $storedfile, $config, false, false);

if ($h5pid !== false) {
    echo "SUCCESS! H5P ID: " . $h5pid . "\n";
} else {
    echo "FAILED - save_h5p returned false\n";

    // Hole Fehler aus dem Framework
    $interface = $factory->get_framework();
    $errors = $interface->getMessages('error');
    if (!empty($errors)) {
        echo "\nErrors from framework:\n";
        foreach($errors as $msg) {
            if (is_object($msg)) {
                // Es ist ein stdClass mit message property
                if (isset($msg->message)) {
                    echo "  - " . $msg->message . "\n";
                } else {
                    echo "  - " . print_r($msg, true) . "\n";
                }
            } else {
                echo "  - " . $msg . "\n";
            }
        }
    }
}

// Prüfe ob es schon einen h5p Eintrag mit diesem pathnamehash gibt
$existing = $DB->get_record('h5p', ['pathnamehash' => $fileinfo->pathnamehash]);
if ($existing) {
    echo "\nExisting h5p entry found with ID: " . $existing->id . "\n";
    echo "Main library ID: " . $existing->mainlibraryid . "\n";
} else {
    echo "\nNo existing h5p entry for this file.\n";
}
