<?php
/* Shared helpers for the website forms. Emails go to CONTACT_TO from myf-config.php,
   which sits one folder ABOVE public_html (never on GitHub). */
function myf_json($code, $ok) { http_response_code($code); echo json_encode(['ok' => $ok]); exit; }

function myf_start() {
    header('Content-Type: application/json');
    header('Cache-Control: no-store');
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') myf_json(405, false);
    // Only accept requests from our own site
    $host = strtolower(preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? ''));
    $origin = $_SERVER['HTTP_ORIGIN'] ?? ($_SERVER['HTTP_REFERER'] ?? '');
    if ($origin !== '' && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== $host) myf_json(403, false);
    $in = json_decode(file_get_contents('php://input'), true) ?: [];
    if (!empty($in['website'])) myf_json(200, true);                  // bot trap: real visitors leave this empty
    return $in;
}

function myf_field($in, $key, $max) {
    return trim(preg_replace('/[\r\n]+/', ' ', substr((string)($in[$key] ?? ''), 0, $max)));
}

function myf_mail($subject, $lines, $replyName, $replyEmail) {
    $cfgFile = dirname(__DIR__, 2) . '/myf-config.php';
    $cfg = is_file($cfgFile) ? require $cfgFile : [];
    $to = $cfg['CONTACT_TO'] ?? '';
    if (!$to) return null;                                             // not configured yet
    $domain = preg_replace('/^www\./', '', strtolower(preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? 'masteryourfinance.org')));
    $from = $cfg['CONTACT_FROM'] ?? "website@$domain";
    $body = '';
    foreach ($lines as $k => $v) $body .= str_pad("$k:", 12) . $v . "\n";
    $body .= 'Time (UTC): ' . gmdate('Y-m-d H:i') . "\n\nReply to this email to answer $replyName directly.\n";
    $headers = "From: Master Your Finance website <$from>\r\nReply-To: $replyName <$replyEmail>\r\nContent-Type: text/plain; charset=UTF-8";
    return @mail($to, '=?UTF-8?B?' . base64_encode($subject) . '?=', $body, $headers, "-f$from");
}
