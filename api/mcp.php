<?php
/*
 * Read-only MCP server (Model Context Protocol, Streamable HTTP transport, JSON responses).
 * Public endpoint: https://masteryourfinance.org/mcp  (see /.well-known/mcp/server-card.json)
 * Tools let AI agents read the site: overview, services, and any page as Markdown.
 * It never sends email or changes anything.
 */
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Accept, Mcp-Session-Id, MCP-Protocol-Version');
header('Cache-Control: no-store');

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method === 'OPTIONS') { http_response_code(204); exit; }
if ($method !== 'POST') {
    http_response_code(405); header('Allow: POST, OPTIONS'); header('Content-Type: application/json');
    echo json_encode(['error' => 'This MCP endpoint accepts JSON-RPC over HTTP POST. See /.well-known/mcp/server-card.json']); exit;
}

const SERVER_NAME = 'masteryourfinance';
const SERVER_VERSION = '1.0.0';
const SUPPORTED = ['2025-06-18', '2025-03-26', '2024-11-05'];
$root = dirname(__DIR__);
$pages = ['index', 'services', 'industries', 'tools', 'about-us', 'contact-us', 'health-check', 'privacy-policy', 'terms'];

$tools = [
    ['name' => 'get_site_overview', 'title' => 'Site overview',
     'description' => 'Summary of Master Your Finance (outsourced finance team for professional service firms in the US, UK and Australia) with links to every page.',
     'inputSchema' => ['type' => 'object', 'properties' => new stdClass()], 'annotations' => ['readOnlyHint' => true]],
    ['name' => 'list_services', 'title' => 'List services',
     'description' => 'The finance services Master Your Finance offers, with a one-line summary of each.',
     'inputSchema' => ['type' => 'object', 'properties' => new stdClass()], 'annotations' => ['readOnlyHint' => true]],
    ['name' => 'read_page', 'title' => 'Read a page',
     'description' => 'Read a page of masteryourfinance.org as Markdown.',
     'inputSchema' => ['type' => 'object', 'properties' => ['page' => ['type' => 'string', 'enum' => $pages, 'description' => 'Page to read']], 'required' => ['page']],
     'annotations' => ['readOnlyHint' => true]],
    ['name' => 'get_booking_link', 'title' => 'Booking link',
     'description' => 'Link to book a free 30-minute finance review call with Master Your Finance.',
     'inputSchema' => ['type' => 'object', 'properties' => new stdClass()], 'annotations' => ['readOnlyHint' => true]],
];
$services = [
    ['name' => 'Bookkeeping & Accounting', 'summary' => 'Clean books, reconciled accounts, and AR/AP handled every week.'],
    ['name' => 'Cash Flow Forecasting', 'summary' => '13-week cash flow forecast; track DSO and chase receivables before they age.'],
    ['name' => 'Monthly Reporting', 'summary' => 'Reports delivered on schedule, with the numbers explained in plain words.'],
    ['name' => 'CFO-Lite Support', 'summary' => 'Guidance on hiring, pricing and growth decisions, without a full-time CFO.'],
    ['name' => 'Finance Operations', 'summary' => 'Receivables and reporting run day to day.'],
];

function reply($id, $result) { return ['jsonrpc' => '2.0', 'id' => $id, 'result' => $result]; }
function fail($id, $code, $msg) { return ['jsonrpc' => '2.0', 'id' => $id, 'error' => ['code' => $code, 'message' => $msg]]; }
function text_result($t, $isError = false) { return ['content' => [['type' => 'text', 'text' => $t]], 'isError' => $isError]; }

function handle($msg) {
    global $tools, $services, $pages, $root;
    if (!is_array($msg) || ($msg['jsonrpc'] ?? '') !== '2.0' || !isset($msg['method'])) return fail($msg['id'] ?? null, -32600, 'Invalid Request');
    $id = $msg['id'] ?? null; $p = $msg['params'] ?? [];
    $isNotification = !array_key_exists('id', $msg);
    switch ($msg['method']) {
        case 'initialize':
            $want = $p['protocolVersion'] ?? SUPPORTED[0];
            return reply($id, [
                'protocolVersion' => in_array($want, SUPPORTED, true) ? $want : SUPPORTED[0],
                'capabilities' => ['tools' => ['listChanged' => false]],
                'serverInfo' => ['name' => SERVER_NAME, 'title' => 'Master Your Finance', 'version' => SERVER_VERSION],
                'instructions' => 'Read-only tools for the Master Your Finance website. Use get_site_overview first, then read_page for details.',
            ]);
        case 'ping': return reply($id, new stdClass());
        case 'tools/list': return reply($id, ['tools' => $tools]);
        case 'tools/call':
            $name = $p['name'] ?? ''; $args = $p['arguments'] ?? [];
            if ($name === 'get_site_overview') return reply($id, text_result((string)@file_get_contents("$root/llms.txt")));
            if ($name === 'list_services') return reply($id, text_result(json_encode($services, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)));
            if ($name === 'get_booking_link') return reply($id, text_result('Book a free 30-minute finance review: https://calendly.com/himanshu-masteryourbusiness/30-minutes-discovery-call-law-firms'));
            if ($name === 'read_page') {
                $page = $args['page'] ?? '';
                if (!in_array($page, $pages, true)) return reply($id, text_result('Unknown page. Choose one of: ' . implode(', ', $pages), true));
                return reply($id, text_result((string)@file_get_contents("$root/$page.md")));
            }
            return fail($id, -32602, "Unknown tool: $name");
        default:
            if ($isNotification) return null;          // e.g. notifications/initialized
            return fail($id, -32601, 'Method not found');
    }
}

$in = json_decode(file_get_contents('php://input'), true);
if ($in === null) { header('Content-Type: application/json'); echo json_encode(fail(null, -32700, 'Parse error')); exit; }
$batch = is_array($in) && array_is_list($in);
$out = [];
foreach ($batch ? $in : [$in] as $m) { $r = handle($m); if ($r !== null) $out[] = $r; }
if (!$out) { http_response_code(202); exit; }                // only notifications
header('Content-Type: application/json');
echo json_encode($batch ? $out : $out[0], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
