<?php
/* "Book a call" form: emails the enquiry to CONTACT_TO (set in myf-config.php). */
require __DIR__ . '/_send.php';
$in = myf_start();
$name = myf_field($in, 'name', 120); $email = myf_field($in, 'email', 200);
if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) myf_json(422, false);
$sent = myf_mail("New call request: $name", [
    'Name' => $name, 'Email' => $email,
    'Firm size' => myf_field($in, 'size', 60), 'Needs' => myf_field($in, 'need', 80), 'Page' => myf_field($in, 'page', 120),
], $name, $email);
if ($sent === null) myf_json(500, false);
myf_json($sent ? 200 : 502, $sent);
