<?php
/**
 * CLI Script to enroll a user in a course
 */
define('CLI_SCRIPT', true);
require('/opt/bitnami/moodle/config.php');
require_once($CFG->libdir . '/enrollib.php');

$userid = 4;  // student1
$courseid = 22;
$roleid = 5;  // student role

$plugin = enrol_get_plugin('manual');
$instance = $DB->get_record('enrol', ['courseid' => $courseid, 'enrol' => 'manual']);

if (!$instance) {
    $course = $DB->get_record('course', ['id' => $courseid]);
    $instanceid = $plugin->add_instance($course);
    $instance = $DB->get_record('enrol', ['id' => $instanceid]);
}

$plugin->enrol_user($instance, $userid, $roleid);
echo "User $userid enrolled in course $courseid with role $roleid\n";
