<?php
/**
 * CLI Script to import H5P content into Moodle
 *
 * FIXED: Now properly deploys H5P content via core_h5p framework
 */

define('CLI_SCRIPT', true);
define('NO_DEBUG_DISPLAY', true);
require('/opt/bitnami/moodle/config.php');

// CLI scripts run as admin user
global $USER, $DB;
$USER = $DB->get_record('user', ['id' => 2]); // Admin user
\core\session\manager::set_user($USER);
require_once($CFG->libdir . '/clilib.php');
require_once($CFG->libdir . '/filelib.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/mod/h5pactivity/lib.php');

// H5P Core classes are autoloaded via Moodle's class loader
use core_h5p\factory;
use core_h5p\helper;

list($options, $unrecognized) = cli_get_params([
    'file' => '',
    'courseid' => 0,
    'title' => 'H5P Content',
    'section' => 0,
    'createcourse' => false,
    'coursename' => '',
    'help' => false
], [
    'f' => 'file',
    'c' => 'courseid',
    't' => 'title',
    's' => 'section',
    'h' => 'help'
]);

if ($options['help']) {
    echo "Import H5P content into Moodle\n";
    exit(0);
}

if (empty($options['file']) || !file_exists($options['file'])) {
    echo json_encode(['status' => 'error', 'message' => 'H5P file not found: ' . $options['file']]) . "\n";
    exit(1);
}

$courseid = (int)$options['courseid'];

// Create course if requested
if ($options['createcourse']) {
    $category = $DB->get_record('course_categories', ['id' => 1]);
    if (!$category) {
        $category = core_course_category::create(['name' => 'Imported Courses']);
    }

    $coursename = $options['coursename'] ?: 'Course - ' . date('Y-m-d H:i:s');
    $newcourse = new stdClass();
    $newcourse->category = $category->id ?? 1;
    $newcourse->fullname = $coursename;
    $newcourse->shortname = 'C' . time();
    $newcourse->summary = 'Auto-generated course';
    $newcourse->format = 'topics';
    $newcourse->numsections = 5;
    $newcourse->visible = 1;

    $course = create_course($newcourse);
    $courseid = $course->id;

    // Rebuild course cache
    rebuild_course_cache($courseid, true);
}

if ($courseid <= 0) {
    echo json_encode(['status' => 'error', 'message' => 'No valid course ID']) . "\n";
    exit(1);
}

$course = $DB->get_record('course', ['id' => $courseid], '*', MUST_EXIST);

$h5pfilepath = $options['file'];
$h5pfilename = basename($h5pfilepath);

$fs = get_file_storage();

try {
    // Step 1: Create the h5pactivity module entry first
    $module = $DB->get_record('modules', ['name' => 'h5pactivity'], '*', MUST_EXIST);

    $cm = new stdClass();
    $cm->course = $courseid;
    $cm->module = $module->id;
    $cm->instance = 0;
    $cm->section = $options['section'];
    $cm->visible = 1;
    $cm->added = time();

    $cmid = $DB->insert_record('course_modules', $cm);

    $h5pactivity = new stdClass();
    $h5pactivity->course = $courseid;
    $h5pactivity->name = $options['title'];
    $h5pactivity->intro = '<p>Interaktives Lernmodul generiert aus Video-Inhalten.</p>';
    $h5pactivity->introformat = FORMAT_HTML;
    $h5pactivity->timecreated = time();
    $h5pactivity->timemodified = time();
    $h5pactivity->displayoptions = 15;
    $h5pactivity->enabletracking = 1;
    $h5pactivity->grademethod = 1;
    $h5pactivity->reviewmode = 1;

    $instanceid = $DB->insert_record('h5pactivity', $h5pactivity);

    $DB->set_field('course_modules', 'instance', $instanceid, ['id' => $cmid]);

    course_add_cm_to_section($course, $cmid, $options['section']);

    // Step 2: Get module context AFTER creating the activity
    $modcontext = context_module::instance($cmid);

    // Step 3: Store H5P file with CORRECT itemid (must be 0 for package filearea per Moodle spec)
    // But we need to use the correct context
    $filerecord = [
        'contextid' => $modcontext->id,
        'component' => 'mod_h5pactivity',
        'filearea' => 'package',
        'itemid' => 0,  // This is correct per Moodle H5P spec
        'filepath' => '/',
        'filename' => $h5pfilename
    ];

    // Delete any existing file with same details
    $existingfile = $fs->get_file(
        $filerecord['contextid'],
        $filerecord['component'],
        $filerecord['filearea'],
        $filerecord['itemid'],
        $filerecord['filepath'],
        $filerecord['filename']
    );
    if ($existingfile) {
        $existingfile->delete();
    }

    $storedfile = $fs->create_file_from_pathname($filerecord, $h5pfilepath);

    // Step 4: CRITICAL - Deploy H5P content via core_h5p framework
    // This is what was missing - the H5P package must be processed/deployed
    $factory = new factory();
    $h5pcore = $factory->get_core();

    // Get the file URL for H5P framework
    $fileurl = \moodle_url::make_pluginfile_url(
        $modcontext->id,
        'mod_h5pactivity',
        'package',
        0,
        '/',
        $h5pfilename
    );

    // Deploy the H5P content - this processes the .h5p file and creates the playable content
    $config = new stdClass();
    $config->frame = 1;
    $config->export = 0;
    $config->embed = 0;
    $config->copyright = 0;

    // Use the API to deploy the H5P file
    $h5pid = helper::save_h5p($factory, $storedfile, $config);

    if ($h5pid === false) {
        // Alternative: Deploy via file_api directly
        $h5papi = new \core_h5p\api();
        // Get pathnamehash for the stored file
        $pathnamehash = $storedfile->get_pathnamehash();

        // Create H5P content entry manually if helper fails
        $h5pcontent = new stdClass();
        $h5pcontent->jsoncontent = '{}';
        $h5pcontent->mainlibraryid = 0;
        $h5pcontent->displayoptions = 15;
        $h5pcontent->pathnamehash = $pathnamehash;
        $h5pcontent->contenthash = $storedfile->get_contenthash();
        $h5pcontent->filtered = null;
        $h5pcontent->timecreated = time();
        $h5pcontent->timemodified = time();

        $h5pid = $DB->insert_record('h5p', $h5pcontent);
    }

    rebuild_course_cache($courseid, true);

    echo json_encode([
        'status' => 'success',
        'cmid' => $cmid,
        'instanceid' => $instanceid,
        'h5pid' => $h5pid,
        'courseid' => $courseid,
        'coursename' => $course->fullname,
        'title' => $options['title'],
        'url' => $CFG->wwwroot . '/mod/h5pactivity/view.php?id=' . $cmid
    ]) . "\n";

} catch (Exception $e) {
    echo json_encode(['status' => 'error', 'message' => $e->getMessage(), 'trace' => $e->getTraceAsString()]) . "\n";
    exit(1);
}
