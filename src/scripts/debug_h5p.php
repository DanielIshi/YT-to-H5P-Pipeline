<?php
/**
 * Debug H5P package deployment
 */
define('CLI_SCRIPT', true);
require('/opt/bitnami/moodle/config.php');
global $USER, $DB;
$USER = $DB->get_record('user', ['id' => 2]);
\core\session\manager::set_user($USER);

use core_h5p\factory;
use core_h5p\api;
use core_h5p\helper;

$fs = get_file_storage();

// Check what packages exist
$sql = "SELECT f.id, f.filename, f.contenthash, f.pathnamehash, ctx.instanceid as cmid
        FROM {files} f
        JOIN {context} ctx ON ctx.id = f.contextid
        WHERE f.component = 'mod_h5pactivity'
        AND f.filearea = 'package'
        AND f.filename != '.'
        ORDER BY f.id DESC
        LIMIT 5";
$files = $DB->get_records_sql($sql);

echo "Found " . count($files) . " H5P packages:\n\n";

foreach ($files as $f) {
    echo "=== File: {$f->filename} (cmid={$f->cmid}) ===\n";
    echo "  pathnamehash: {$f->pathnamehash}\n";

    $storedfile = $fs->get_file_by_hash($f->pathnamehash);
    if (!$storedfile) {
        echo "  ERROR: File not found in storage!\n";
        continue;
    }

    echo "  File size: " . $storedfile->get_filesize() . " bytes\n";

    // Try to validate the package
    $factory = new factory();
    $valid = api::is_valid_package($storedfile, false, false, $factory, false);
    echo "  Valid package: " . ($valid ? "YES" : "NO") . "\n";

    if (!$valid) {
        // Get validation errors from the framework
        $core = $factory->get_core();
        $framework = $core->h5pF;

        // Check for messages
        $messages = $framework->getMessages('error');
        if (!empty($messages)) {
            echo "  Framework errors:\n";
            foreach ($messages as $msg) {
                echo "    - " . $msg->message . "\n";
            }
        }

        // Also check info messages
        $info = $framework->getMessages('info');
        if (!empty($info)) {
            echo "  Framework info:\n";
            foreach ($info as $msg) {
                echo "    - " . $msg->message . "\n";
            }
        }
    }

    // Try to deploy
    if ($valid) {
        $config = new stdClass();
        $config->frame = 1;
        $config->export = 0;
        $config->embed = 0;
        $config->copyright = 0;

        $h5pid = helper::save_h5p($factory, $storedfile, $config);
        echo "  Deployed H5P ID: " . ($h5pid ?: "FAILED") . "\n";
    }

    echo "\n";
}
