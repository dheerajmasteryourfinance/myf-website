<?php
/*
 * Health check lead capture: saves name + email to Airtable.
 * The Airtable token is NOT in this file. It lives in myf-config.php, one folder
 * ABOVE public_html, so nobody can download it from the website.
 * See README.md, section "Airtable token".
 */
header('Content-Type: application/json');
header('Cache-Control: no-store');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo '{"ok":false}'; exit; }

// Only accept requests from our own site
$host = $_SERVER['HTTP_HOST'] ?? '';
$origin = $_SERVER['HTTP_ORIGIN'] ?? ($_SERVER['HTTP_REFERER'] ?? '');
if ($origin !== '' && parse_url($origin, PHP_URL_HOST) !== $host) { http_response_code(403); echo '{"ok":false}'; exit; }

$cfgFile = dirname(__DIR__, 2) . '/myf-config.php';   // e.g. domains/masteryourfinance.org/myf-config.php
$cfg = is_file($cfgFile) ? require $cfgFile : [];
$token = $cfg['AIRTABLE_TOKEN'] ?? getenv('AIRTABLE_TOKEN');
if (!$token) { http_response_code(500); echo '{"ok":false,"error":"not configured"}'; exit; }

$in = json_decode(file_get_contents('php://input'), true) ?: [];
$name  = trim(substr((string)($in['name'] ?? ''), 0, 120));
$email = trim(substr((string)($in['email'] ?? ''), 0, 200));
if (!empty($in['website'])) { echo '{"ok":true}'; exit; }          // bot trap: real visitors leave this empty
if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) { http_response_code(422); echo '{"ok":false}'; exit; }

$base  = 'appnvzj2hl731uVhc';
$table = 'tblGuSpwMsEiDHjrC';
$body = json_encode(['records' => [['fields' => [
    'fldQyJFfRPPAQpmRE' => $name,
    'flde5cGK654cdAtqe' => $email,
]]], 'typecast' => true]);

$ch = curl_init("https://api.airtable.com/v0/$base/$table");
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $body,
    CURLOPT_HTTPHEADER => ["Authorization: Bearer $token", 'Content-Type: application/json'],
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 10,
]);
curl_exec($ch);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

$ok = $code >= 200 && $code < 300;
http_response_code($ok ? 200 : 502);
echo json_encode(['ok' => $ok]);
