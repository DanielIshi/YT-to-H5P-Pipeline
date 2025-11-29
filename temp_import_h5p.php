<?php
define("CLI_SCRIPT", true);
require(__DIR__ . "/../config.php");
require_once($CFG->libdir . "/clilib.php");
require_once($CFG->libdir . "/filelib.php");
require_once($CFG->dirroot . "/course/lib.php");
require_once($CFG->dirroot . "/course/modlib.php");
require_once($CFG->dirroot . "/mod/h5pactivity/lib.php");
require_once($CFG->libdir . "/enrollib.php");

list($options, $unrecognized) = cli_get_params([
    "file" => "",
    "course" => "",
    "coursename" => "",
    "title" => "",
    "section" => 1,
    "help" => false
], ["f" => "file", "c" => "course", "n" => "coursename", "t" => "title", "s" => "section", "h" => "help"]);

if ($options["help"] || empty($options["file"])) {
    echo "Usage: php import_h5p.php --file=/path/to/file.h5p [--course=ID] [--coursename=NAME] [--title=TITLE] [--section=N]\n";
    exit(0);
}

$filepath = $options["file"];
if (!file_exists($filepath)) {
    echo json_encode(["status" => "error", "message" => "File not found: $filepath"]);
    exit(1);
}

// Set admin user for CLI operations
$admin = get_admin();
\core\session\manager::set_user($admin);

// Create course if coursename provided and course not specified
if (!empty($options["coursename"]) && empty($options["course"])) {
    $coursedata = new stdClass();
    $coursedata->fullname = $options["coursename"];
    $coursedata->shortname = substr(preg_replace("/[^a-zA-Z0-9]/", "", $options["coursename"]), 0, 20) . "_" . time();
    $coursedata->category = 1;
    $coursedata->format = "topics";
    $coursedata->numsections = 1;

    $course = create_course($coursedata);
    $courseid = $course->id;
    $course_created = true;

    // Enroll admin as teacher in the new course
    $context = context_course::instance($courseid);
    $teacherrole = $DB->get_record('role', ['shortname' => 'editingteacher']);
    if ($teacherrole) {
        role_assign($teacherrole->id, $admin->id, $context->id);
        $enrolplugin = enrol_get_plugin('manual');
        $enrolinstance = $DB->get_record('enrol', ['courseid' => $courseid, 'enrol' => 'manual']);
        if (!$enrolinstance) {
            $enrolinstance = $enrolplugin->add_instance($course);
            $enrolinstance = $DB->get_record('enrol', ['id' => $enrolinstance]);
        }
        $enrolplugin->enrol_user($enrolinstance, $admin->id, $teacherrole->id);
    }
} else {
    $course_created = false;
    $courseid = (int)$options["course"] ?: 1;
}

$course = get_course($courseid);
$context = context_course::instance($courseid);

// Get activity title
$activitytitle = !empty($options["title"]) ? $options["title"] : pathinfo(basename($filepath), PATHINFO_FILENAME);

// Upload H5P file as draft file (required for h5pactivity)
$fs = get_file_storage();
$filename = basename($filepath);

// Create a unique draft itemid
$draftitemid = file_get_unused_draft_itemid();

// User context for draft files
$usercontext = context_user::instance($admin->id);

$filerecord = [
    "contextid" => $usercontext->id,
    "component" => "user",
    "filearea" => "draft",
    "itemid" => $draftitemid,
    "filepath" => "/",
    "filename" => $filename,
    "userid" => $admin->id
];

// Remove existing draft file if present
$existing = $fs->get_file($filerecord["contextid"], $filerecord["component"], $filerecord["filearea"],
    $filerecord["itemid"], $filerecord["filepath"], $filerecord["filename"]);
if ($existing) {
    $existing->delete();
}

$file = $fs->create_file_from_pathname($filerecord, $filepath);

if (!$file) {
    echo json_encode(["status" => "error", "message" => "Failed to create draft file"]);
    exit(1);
}

// Create H5P activity in course
try {
    $modulename = 'h5pactivity';
    $module = $DB->get_record('modules', ['name' => $modulename], '*', MUST_EXIST);

    // Get the section
    $sectionnum = (int)$options["section"];
    $section = $DB->get_record('course_sections', ['course' => $courseid, 'section' => $sectionnum]);
    if (!$section) {
        // Create section if it doesn't exist
        $section = course_create_section($courseid, $sectionnum);
    }

    // Prepare module info
    $moduleinfo = new stdClass();
    $moduleinfo->modulename = $modulename;
    $moduleinfo->module = $module->id;
    $moduleinfo->name = $activitytitle;
    $moduleinfo->intro = '<p>Interaktives Lernmodul generiert aus Video-Inhalten.</p>';
    $moduleinfo->introformat = FORMAT_HTML;
    $moduleinfo->showdescription = 0;
    $moduleinfo->course = $courseid;
    $moduleinfo->section = $sectionnum;
    $moduleinfo->visible = 1;
    $moduleinfo->visibleoncoursepage = 1;
    $moduleinfo->cmidnumber = '';
    $moduleinfo->groupmode = 0;
    $moduleinfo->groupingid = 0;
    $moduleinfo->availability = null;
    $moduleinfo->completion = 0;

    // H5P specific settings - packagefile is the draft itemid
    $moduleinfo->packagefile = $draftitemid;
    $moduleinfo->displayoptions = 15; // Show all options
    $moduleinfo->enabletracking = 1;
    $moduleinfo->grademethod = 1; // Highest grade
    $moduleinfo->reviewmode = 1; // When completed
    $moduleinfo->grade = 100;

    // Create the module
    $moduleinfo = add_moduleinfo($moduleinfo, $course);

    echo json_encode([
        "status" => "success",
        "message" => "H5P activity created in course",
        "course_id" => $courseid,
        "course_created" => $course_created,
        "activity_id" => $moduleinfo->coursemodule,
        "activity_name" => $activitytitle,
        "course_url" => $CFG->wwwroot . "/course/view.php?id=" . $courseid,
        "activity_url" => $CFG->wwwroot . "/mod/h5pactivity/view.php?id=" . $moduleinfo->coursemodule
    ]);
} catch (Exception $e) {
    echo json_encode([
        "status" => "error",
        "message" => "Activity creation failed: " . $e->getMessage(),
        "course_id" => $courseid,
        "course_created" => $course_created,
        "trace" => $e->getTraceAsString()
    ]);
    exit(1);
}
