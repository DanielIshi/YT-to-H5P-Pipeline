<?php
/**
 * CLI Script to import H5P content into Moodle
 */

define('CLI_SCRIPT', true);
require('/opt/bitnami/moodle/config.php');
require_once($CFG->libdir . '/clilib.php');
require_once($CFG->libdir . '/filelib.php');
require_once($CFG->dirroot . '/course/lib.php');
require_once($CFG->dirroot . '/mod/h5pactivity/lib.php');

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
$coursecontext = context_course::instance($courseid);

$h5pfilepath = $options['file'];
$h5pfilename = basename($h5pfilepath);

$fs = get_file_storage();

$filerecord = [
    'contextid' => $coursecontext->id,
    'component' => 'mod_h5pactivity',
    'filearea' => 'package',
    'itemid' => 0,
    'filepath' => '/',
    'filename' => $h5pfilename
];

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

try {
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
    $h5pactivity->intro = '<p>Auto-imported H5P content</p>';
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

    $modcontext = context_module::instance($cmid);
    $newfilerecord = [
        'contextid' => $modcontext->id,
        'component' => 'mod_h5pactivity',
        'filearea' => 'package',
        'itemid' => 0,
        'filepath' => '/',
        'filename' => $h5pfilename
    ];

    $newfile = $fs->create_file_from_storedfile($newfilerecord, $storedfile);
    $storedfile->delete();

    rebuild_course_cache($courseid, true);

    echo json_encode([
        'status' => 'success',
        'cmid' => $cmid,
        'instanceid' => $instanceid,
        'courseid' => $courseid,
        'coursename' => $course->fullname,
        'title' => $options['title'],
        'url' => $CFG->wwwroot . '/mod/h5pactivity/view.php?id=' . $cmid
    ]) . "\n";

} catch (Exception $e) {
    echo json_encode(['status' => 'error', 'message' => $e->getMessage()]) . "\n";
    exit(1);
}
