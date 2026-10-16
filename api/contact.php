<?php
/*
 * "Book a call" form: emails the enquiry to the team and (optionally) saves it to Airtable.
 * Settings live in myf-config.php, one folder ABOVE public_html (see myf-config.example.php).
 * Nothing secret is in this file or in the website pages.
 */
header('Content-Type: application/json');
header('Cache-Control: no-store');

function out($code, $ok) { http_response_code($code); echo json_encode(['ok' => $ok]); exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(405, false);

// Only accept requests from our own site
$host = $_SERVER['HTTP_HOST'] ?? '';
$origin = $_SERVER['HTTP_ORIGIN'] ?? ($_SERVER['HTTP_REFERER'] ?? '');
if ($origin !== '' && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== strtolower(preg_replace('/:\d+$/', '', $host))) out(403, false);

$cfgFile = dirname(__DIR__, 2) . '/myf-config.php';
$cfg = is_file($cfgFile) ? require $cfgFile : [];

$in = json_decode(file_get_contents('php://input'), true) ?: [];
if (!empty($in['website'])) out(200, true);                       // bot trap: real visitors leave this empty
$clip = function ($k, $n) use ($in) { return trim(preg_replace('/[\r\n]+/', ' ', substr((string)($in[$k] ?? ''), 0, $n))); };
$name = $clip('name', 120); $email = $clip('email', 200);
$size = $clip('size', 60);  $need  = $clip('need', 80);  $page = $clip('page', 120);
if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) out(422, false);

$sent = false;

// 1) Email to the team
$to = $cfg['CONTACT_TO'] ?? '';
if ($to) {
    $domain = preg_replace('/^www\./', '', $host);
    $from = $cfg['CONTACT_FROM'] ?? "website@$domain";
    $subject = "New call request: $name";
    $body = "New enquiry from the website\n\n"
          . "Name:       $name\nEmail:      $email\nFirm size:  $size\nNeeds:      $need\nPage:       $page\n"
          . "Time (UTC): " . gmdate('Y-m-d H:i') . "\n\nReply to this email to answer $name directly.\n";
    $headers = "From: Master Your Finance website <$from>\r\nReply-To: $name <$email>\r\nContent-Type: text/plain; charset=UTF-8";
    $sent = @mail($to, '=?UTF-8?B?' . base64_encode($subject) . '?=', $body, $headers, "-f$from") || $sent;
}

// 2) Airtable (optional: only if a table is set in the config)
$token = $cfg['AIRTABLE_TOKEN'] ?? ''; $base = $cfg['CONTACT_AIRTABLE_BASE'] ?? ''; $table = $cfg['CONTACT_AIRTABLE_TABLE'] ?? '';
if ($token && $base && $table) {
    $ch = curl_init('https://api.airtable.com/v0/' . rawurlencode($base) . '/' . rawurlencode($table));
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode(['typecast' => true, 'records' => [['fields' => [
            'Name' => $name, 'Email' => $email, 'Firm size' => $size, 'Needs' => $need, 'Page' => $page,
        ]]]]),
        CURLOPT_HTTPHEADER => ["Authorization: Bearer $token", 'Content-Type: application/json'],
        CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10,
    ]);
    curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    $sent = ($code >= 200 && $code < 300) || $sent;
}

if (!$to && !($token && $base && $table)) out(500, false);         // nothing configured yet
out($sent ? 200 : 502, $sent);
