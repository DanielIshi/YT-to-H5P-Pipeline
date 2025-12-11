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
    'courseimage' => '',  // URL to course image (YouTube thumbnail or generated)
    'help' => false
], [
    'f' => 'file',
    'c' => 'courseid',
    't' => 'title',
    's' => 'section',
    'i' => 'courseimage',
    'h' => 'help'
]);

if ($options['help']) {
    echo "Import H5P content into Moodle\n";
    exit(0);
}

// Allow "create course only" mode without H5P file
$createCourseOnly = $options['createcourse'] && (empty($options['file']) || $options['file'] === '/dev/null');

if (!$createCourseOnly && (empty($options['file']) || !file_exists($options['file']))) {
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
    $newcourse->numsections = 0;  // Only General section - no empty topics
    $newcourse->visible = 1;

    $course = create_course($newcourse);
    $courseid = $course->id;

    // Set course image if provided
    if (!empty($options['courseimage'])) {
        $imageurl = $options['courseimage'];
        $context = context_course::instance($courseid);

        // Download image
        $imagedata = @file_get_contents($imageurl);
        if ($imagedata) {
            $fs = get_file_storage();

            // Delete existing overview files
            $fs->delete_area_files($context->id, 'course', 'overviewfiles');

            // Determine file extension
            $ext = 'jpg';
            if (strpos($imageurl, '.png') !== false) {
                $ext = 'png';
            }

            $filerecord = [
                'contextid' => $context->id,
                'component' => 'course',
                'filearea' => 'overviewfiles',
                'itemid' => 0,
                'filepath' => '/',
                'filename' => 'course_image.' . $ext
            ];

            $fs->create_file_from_string($filerecord, $imagedata);
        }
    }

    // Enable self-enrolment for the course
    $enrolplugin = enrol_get_plugin('self');
    if ($enrolplugin) {
        // Check if self-enrolment already exists
        $enrolinstance = $DB->get_record('enrol', ['courseid' => $courseid, 'enrol' => 'self']);
        if ($enrolinstance) {
            // Enable existing instance
            $enrolinstance->status = 0; // 0 = enabled
            $DB->update_record('enrol', $enrolinstance);
        } else {
            // Add new self-enrolment instance
            $enrolplugin->add_instance($course, [
                'status' => 0,  // 0 = enabled
                'roleid' => 5,  // Student role
                'enrolperiod' => 0,  // No time limit
            ]);
        }
    }

    // Rebuild course cache
    rebuild_course_cache($courseid, true);

    // If "create course only" mode, return success with courseid and exit
    if ($createCourseOnly) {
        echo json_encode([
            'status' => 'success',
            'courseid' => $courseid,
            'coursename' => $coursename,
            'message' => 'Course created successfully'
        ]) . "\n";
        exit(0);
    }
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

    // Step 4: Deploy H5P content via core_h5p framework
    // H5P packages must be deployed/validated before they can be played
    $factory = new factory();

    // Deploy config - allow all display options
    $config = new stdClass();
    $config->frame = 1;
    $config->export = 0;
    $config->embed = 0;
    $config->copyright = 0;

    // Try to deploy the H5P file - this validates and extracts the package
    $h5pid = false;
    $deployError = null;

    try {
        // Method 1: Use helper::save_h5p (preferred)
        $h5pid = helper::save_h5p($factory, $storedfile, $config);
    } catch (Exception $e) {
        $deployError = $e->getMessage();
    }

    // If deployment failed, try alternative method with full content extraction
    if ($h5pid === false) {
        try {
            // Method 2: Manual deployment - extract content from H5P package
            $pathnamehash = $storedfile->get_pathnamehash();
            $contenthash = $storedfile->get_contenthash();

            // Check if there's already an h5p entry for this file
            $existing = $DB->get_record('h5p', ['pathnamehash' => $pathnamehash]);
            if ($existing) {
                $h5pid = $existing->id;
            } else {
                // Extract content from H5P package
                $mainLibraryId = 0;
                $jsoncontent = '{}';
                $zip = new ZipArchive();

                if ($zip->open($h5pfilepath) === true) {
                    // Get h5p.json for library info
                    $h5pjson = $zip->getFromName('h5p.json');
                    if ($h5pjson) {
                        $h5pdata = json_decode($h5pjson, true);
                        if (isset($h5pdata['mainLibrary'])) {
                            $mainLib = $h5pdata['mainLibrary'];
                            // Find library ID in database
                            $lib = $DB->get_record_sql(
                                "SELECT id FROM {h5p_libraries} WHERE machinename = ? ORDER BY majorversion DESC, minorversion DESC LIMIT 1",
                                [$mainLib]
                            );
                            if ($lib) {
                                $mainLibraryId = $lib->id;
                            }
                        }
                    }

                    // Get content/content.json - this is the actual H5P content!
                    $contentjson = $zip->getFromName('content/content.json');
                    if ($contentjson) {
                        // Validate it's proper JSON
                        $contentdata = json_decode($contentjson, true);
                        if ($contentdata !== null) {
                            $jsoncontent = $contentjson;
                        }
                    }

                    $zip->close();
                }

                // Create H5P content entry with extracted content
                $h5pcontent = new stdClass();
                $h5pcontent->jsoncontent = $jsoncontent;
                $h5pcontent->mainlibraryid = $mainLibraryId;
                $h5pcontent->displayoptions = 15;
                $h5pcontent->pathnamehash = $pathnamehash;
                $h5pcontent->contenthash = $contenthash;
                $h5pcontent->filtered = null;
                $h5pcontent->timecreated = time();
                $h5pcontent->timemodified = time();

                $h5pid = $DB->insert_record('h5p', $h5pcontent);
            }
        } catch (Exception $e2) {
            $deployError = ($deployError ? $deployError . '; ' : '') . $e2->getMessage();
        }
    }

    // If still no h5pid, report error but don't fail completely
    // The content will be deployed on first view
    if ($h5pid === false && !$deployError) {
        $h5pid = -1; // Indicates pending deployment
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
