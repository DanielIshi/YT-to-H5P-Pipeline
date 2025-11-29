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
$sql = "SELECT f.pathnamehash, f.filename, f.contextid, ctx.instanceid as cmid
         FROM {files} f
         JOIN {context} ctx ON ctx.id = f.contextid
         WHERE f.component = 'mod_h5pactivity'
         AND f.filearea = 'package'
         AND f.filename != '.'
         ORDER BY f.id DESC
         LIMIT 1";

$fileinfo = $DB->get_record_sql($sql);
echo "Processing: " . $fileinfo->filename . "\n";

$fs = get_file_storage();
$storedfile = $fs->get_file_by_hash($fileinfo->pathnamehash);

// Factory und Core erstellen
$factory = new factory();

// Temporäres Verzeichnis erstellen
$tempdir = $CFG->tempdir . '/h5pdebug_' . time();
mkdir($tempdir, 0777, true);

$filepath = $tempdir . '/' . $storedfile->get_filename();
$storedfile->copy_content_to($filepath);
echo "Copied to: " . $filepath . "\n";

// Manuell validieren
$validator = $factory->get_validator();

echo "\n=== VALIDATING PACKAGE ===\n";
$valid = $validator->isValidPackage($filepath, false, false);

if ($valid) {
    echo "Package is VALID!\n";

    // Prüfe h5p.json
    $h5pdata = $validator->getH5pData();
    echo "Main library: " . $h5pdata['mainLibrary'] . "\n";
    echo "Dependencies:\n";
    if (isset($h5pdata['preloadedDependencies'])) {
        foreach($h5pdata['preloadedDependencies'] as $dep) {
            echo "  - " . $dep['machineName'] . " " . $dep['majorVersion'] . "." . $dep['minorVersion'] . "\n";
        }
    }

    // Prüfe ob Libraries in DB existieren
    echo "\n=== CHECKING LIBRARY AVAILABILITY ===\n";
    foreach($h5pdata['preloadedDependencies'] as $dep) {
        $lib = $DB->get_record_sql(
            "SELECT id, machinename, majorversion, minorversion FROM {h5p_libraries}
             WHERE machinename = ? AND majorversion = ? AND minorversion >= ?
             ORDER BY minorversion DESC LIMIT 1",
            [$dep['machineName'], $dep['majorVersion'], $dep['minorVersion']]
        );
        if ($lib) {
            echo "  OK: " . $lib->machinename . " " . $lib->majorversion . "." . $lib->minorversion . " (ID: " . $lib->id . ")\n";
        } else {
            echo "  MISSING: " . $dep['machineName'] . " " . $dep['majorVersion'] . "." . $dep['minorVersion'] . "\n";
        }
    }
} else {
    echo "Package is INVALID!\n";
}

// Fehler-Nachrichten
$interface = $factory->get_framework();
$errors = $interface->getMessages('error');
if (!empty($errors)) {
    echo "\nERRORS:\n";
    foreach($errors as $msg) {
        echo "  - " . $msg . "\n";
    }
}

$infos = $interface->getMessages('info');
if (!empty($infos)) {
    echo "\nINFO:\n";
    foreach($infos as $msg) {
        echo "  - " . $msg . "\n";
    }
}

// Aufräumen
exec('rm -rf ' . escapeshellarg($tempdir));
