<?php
// Copy this file to myf-config.php and put it ONE FOLDER ABOVE public_html on Hostinger
// (never inside public_html, never on GitHub). Fill in what you use; leave the rest empty.
return [
    // Airtable personal access token (scope: data.records:write, only the bases below)
    'AIRTABLE_TOKEN' => 'pat_PASTE_YOUR_TOKEN_HERE',

    // "Book a call" form: who gets the enquiry email
    'CONTACT_TO'   => 'you@masteryourfinance.org',
    // Sender address (best: a real mailbox on this domain, created in hPanel > Emails)
    'CONTACT_FROM' => 'website@masteryourfinance.org',

    // Optional: also save "Book a call" enquiries to Airtable.
    // Table needs fields named: Name, Email, Firm size, Needs, Page
    'CONTACT_AIRTABLE_BASE'  => '',   // e.g. appXXXXXXXXXXXXXX
    'CONTACT_AIRTABLE_TABLE' => '',   // e.g. tblXXXXXXXXXXXXXX or the table name
];
