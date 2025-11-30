<?php
define('CLI_SCRIPT', true);
require('/bitnami/moodle/config.php');
require_once($CFG->libdir . '/filelib.php');

use core_h5p\factory;
use core_h5p\helper;

error_reporting(E_ALL);
ini_set('display_errors', 1);

// Activity 24 (cmid)
$cmid = 24;
$context = context_module::instance($cmid);

echo "Context ID: " . $context->id . "\n";

$fs = get_file_storage();
$files = $fs->get_area_files($context->id, 'mod_h5pactivity', 'package', 0, 'id', false);
$storedfile = reset($files);

if (!$storedfile) {
    die("No file found!\n");
}

echo "Processing: " . $storedfile->get_filename() . "\n";
echo "Pathname hash: " . $storedfile->get_pathnamehash() . "\n";

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

    // Prüfe den erstellten Content
    $h5p = $DB->get_record('h5p', ['id' => $h5pid]);
    if ($h5p) {
        echo "Main library ID: " . $h5p->mainlibraryid . "\n";
        echo "JSON Content (first 200 chars): " . substr($h5p->jsoncontent, 0, 200) . "...\n";
    }
} else {
    echo "FAILED - save_h5p returned false\n";

    $interface = $factory->get_framework();
    $errors = $interface->getMessages('error');
    if (!empty($errors)) {
        echo "\nErrors:\n";
        foreach($errors as $msg) {
            if (is_object($msg) && isset($msg->message)) {
                echo "  - " . $msg->message . "\n";
            } else {
                echo "  - " . print_r($msg, true) . "\n";
            }
        }
    }
}
