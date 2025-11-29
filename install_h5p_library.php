<?php
define('CLI_SCRIPT', true);
require('/bitnami/moodle/config.php');
require_once($CFG->libdir . '/filelib.php');

use core_h5p\factory;

error_reporting(E_ALL);
ini_set('display_errors', 1);

$h5pfile = '/tmp/h5p_components.h5p';

echo "Installing H5P library from: $h5pfile\n";

// Factory erstellen
$factory = new factory();

// Temporäres Verzeichnis
$tempdir = $CFG->tempdir . '/h5p_install_' . time();
mkdir($tempdir, 0777, true);

// Entpacken
$zip = new ZipArchive();
if ($zip->open($h5pfile) === TRUE) {
    $zip->extractTo($tempdir);
    $zip->close();
    echo "Extracted to: $tempdir\n";
} else {
    die("Failed to open zip file\n");
}

// Suche nach library.json
$libraryDir = null;
$files = scandir($tempdir);
foreach ($files as $file) {
    if (is_dir($tempdir . '/' . $file) && $file != '.' && $file != '..') {
        if (file_exists($tempdir . '/' . $file . '/library.json')) {
            $libraryDir = $tempdir . '/' . $file;
            break;
        }
    }
}

if (!$libraryDir) {
    die("No library.json found in package\n");
}

echo "Found library in: $libraryDir\n";

// Lese library.json
$libraryJson = json_decode(file_get_contents($libraryDir . '/library.json'), true);
echo "Library: " . $libraryJson['machineName'] . " " . $libraryJson['majorVersion'] . "." . $libraryJson['minorVersion'] . "\n";

// Prüfe ob Library schon existiert
$existingLib = $DB->get_record('h5p_libraries', [
    'machinename' => $libraryJson['machineName'],
    'majorversion' => $libraryJson['majorVersion'],
    'minorversion' => $libraryJson['minorVersion']
]);

if ($existingLib) {
    echo "Library already exists with ID: " . $existingLib->id . "\n";
    echo "Updating...\n";
    $libraryId = $existingLib->id;
} else {
    echo "Creating new library entry...\n";

    // Library-Eintrag erstellen
    $library = new stdClass();
    $library->machinename = $libraryJson['machineName'];
    $library->title = $libraryJson['title'] ?? $libraryJson['machineName'];
    $library->majorversion = $libraryJson['majorVersion'];
    $library->minorversion = $libraryJson['minorVersion'];
    $library->patchversion = $libraryJson['patchVersion'] ?? 0;
    $library->runnable = $libraryJson['runnable'] ?? 0;
    $library->fullscreen = $libraryJson['fullscreen'] ?? 0;
    $library->embedtypes = isset($libraryJson['embedTypes']) ? implode(', ', $libraryJson['embedTypes']) : '';
    $library->preloadedjs = isset($libraryJson['preloadedJs']) ? json_encode(array_column($libraryJson['preloadedJs'], 'path')) : '';
    $library->preloadedcss = isset($libraryJson['preloadedCss']) ? json_encode(array_column($libraryJson['preloadedCss'], 'path')) : '';
    $library->droplibrarycss = '';
    $library->semantics = '';
    $library->addto = '';
    $library->coremajor = $libraryJson['coreApi']['majorVersion'] ?? 1;
    $library->coreminor = $libraryJson['coreApi']['minorVersion'] ?? 0;
    $library->metadatasettings = '';
    $library->tutorial = '';
    $library->example = '';
    $library->enabled = 1;

    $libraryId = $DB->insert_record('h5p_libraries', $library);
    echo "Library created with ID: $libraryId\n";
}

// Speichere die Dateien im Moodle-Filestorage
$fs = get_file_storage();
$syscontext = context_system::instance();

// Lösche alte Dateien falls vorhanden
$fs->delete_area_files($syscontext->id, 'core_h5p', 'libraries', $libraryId);

// Füge alle Dateien aus dem Library-Verzeichnis hinzu
function addFilesRecursive($fs, $syscontext, $libraryId, $sourceDir, $targetPath = '/') {
    $machineName = basename($sourceDir);
    $basePath = '/' . $machineName . '/';

    $files = scandir($sourceDir);
    foreach ($files as $file) {
        if ($file == '.' || $file == '..') continue;

        $fullPath = $sourceDir . '/' . $file;
        $filePath = $targetPath . $file;

        if (is_dir($fullPath)) {
            // Rekursiv für Unterverzeichnisse
            addFilesRecursive($fs, $syscontext, $libraryId, $fullPath, $targetPath . $file . '/');
        } else {
            // Datei hinzufügen
            $fileinfo = [
                'contextid' => $syscontext->id,
                'component' => 'core_h5p',
                'filearea' => 'libraries',
                'itemid' => $libraryId,
                'filepath' => $basePath . ltrim($targetPath, '/'),
                'filename' => $file
            ];

            echo "  Adding: " . $basePath . ltrim($targetPath, '/') . $file . "\n";
            $fs->create_file_from_pathname($fileinfo, $fullPath);
        }
    }
}

addFilesRecursive($fs, $syscontext, $libraryId, $libraryDir, '/');

// Füge Dependencies hinzu
if (isset($libraryJson['preloadedDependencies'])) {
    echo "\nAdding dependencies...\n";
    foreach ($libraryJson['preloadedDependencies'] as $dep) {
        $requiredLib = $DB->get_record_sql(
            "SELECT id FROM {h5p_libraries} WHERE machinename = ? AND majorversion = ? ORDER BY minorversion DESC LIMIT 1",
            [$dep['machineName'], $dep['majorVersion']]
        );

        if ($requiredLib) {
            // Prüfe ob Dependency schon existiert
            $existing = $DB->get_record('h5p_library_dependencies', [
                'libraryid' => $libraryId,
                'requiredlibraryid' => $requiredLib->id
            ]);

            if (!$existing) {
                $dependency = new stdClass();
                $dependency->libraryid = $libraryId;
                $dependency->requiredlibraryid = $requiredLib->id;
                $dependency->dependencytype = 'preloaded';
                $DB->insert_record('h5p_library_dependencies', $dependency);
                echo "  Added dependency: " . $dep['machineName'] . " " . $dep['majorVersion'] . "\n";
            }
        } else {
            echo "  WARNING: Required library not found: " . $dep['machineName'] . " " . $dep['majorVersion'] . "\n";
        }
    }
}

// Aufräumen
exec('rm -rf ' . escapeshellarg($tempdir));

echo "\nLibrary installation complete!\n";

// Prüfe Installation
$lib = $DB->get_record('h5p_libraries', ['id' => $libraryId]);
echo "Installed: " . $lib->machinename . " " . $lib->majorversion . "." . $lib->minorversion . "." . $lib->patchversion . "\n";

$filecount = $DB->count_records_sql("SELECT COUNT(*) FROM {files} WHERE component = 'core_h5p' AND filearea = 'libraries' AND itemid = ? AND filename != '.'", [$libraryId]);
echo "Files: $filecount\n";
