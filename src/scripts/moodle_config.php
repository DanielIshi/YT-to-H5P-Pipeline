<?php  // Moodle configuration file

unset($CFG);
global $CFG;
$CFG = new stdClass();

$CFG->dbtype    = "mariadb";
$CFG->dblibrary = "native";
$CFG->dbhost    = "mariadb";
$CFG->dbname    = "bitnami_moodle";
$CFG->dbuser    = "bn_moodle";
$CFG->dbpass    = "moodle_db_pass_2025";
$CFG->prefix    = "mdl_";
$CFG->dboptions = array (
  "dbpersist" => 0,
  "dbport" => 3306,
  "dbsocket" => "",
  "dbcollation" => "utf8mb4_unicode_ci",
);

// Fixed wwwroot for reverse proxy setup
$CFG->wwwroot   = "https://moodle.srv947487.hstgr.cloud";
$CFG->dataroot  = "/bitnami/moodledata";
$CFG->admin     = "admin";

$CFG->directorypermissions = 0777;

// SSL Proxy - Caddy terminates SSL
$CFG->sslproxy = true;

// Debug settings
$CFG->debug = E_ALL;
$CFG->debugdisplay = 1;

// Cookie settings for H5P iframe embedding
$CFG->cookiesecure = true;
$CFG->cookiehttponly = true;
$CFG->sessioncookie = '';
$CFG->sessioncookiepath = '/';
$CFG->cookiesamesite = 'None';

require_once(__DIR__ . "/lib/setup.php");
