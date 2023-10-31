<?php

/**
 * Capture values for specific Drupal node entities.
 *
 * This script is used by a temporary process for retrieving summary
 * documents created directly in Drupal (rather than being imported
 * from the CDR) in order to generate XML for import into the CDR
 * so the summaries can be shared with our PDQ data partners. The
 * longer-term solution will use the nodes2xml.py script, which pulls
 * the documents from Drupal using the JSON API service. That solution
 * depends on the Drupal core JSON:API module being enabled. Until
 * that happens (no timeline projected as of this writing), we will
 * need to use this more manual process.
 *
 * The process for this temporary solution involves the following steps:
 *
 *  1. Log in via SSH to one of the production cancer.gov Drupal servers.
 *  2. Create a new directory somewhere on the server.
 *  3. Copy this script to that directory.
 *  4. Edit the script, setting the $directory variable to the path for
 *     this new directory, and setting the $nids variable to the list
 *     of integer IDs for the nodes to be collected (provided by CIAT).
 *  5. Use drush to run the php script.
 *  6. Create a tar file containing the .json files created by the script.
 *  7. Copy that tar file to a local host for further processing.
 *  8. Unpack the tar file in a new directory on the local host.
 *  9. Run create-svpc-summaries-from-drupal-json.py (contained in the
 *     same directory as this script in the version control repository)
 *     in the new directory using a Python 3 virtual environment with
 *     the third-party lxml and requests modules installed.
 * 10. Give CIAT the .xml files created by that script.
 */

$directory = '/path/to/desired/output/directory';
$nids = [ /* list of integers for node IDs */ ];

foreach ($nids as $nid) {
  $node = \Drupal\node\Entity\Node::load($nid);
  if (empty($node)) {
    echo "node $nid not found\n";
    continue;
  }
  foreach (['en', 'es'] as $code) {
    if ($node->hasTranslation($code)) {
      $translation = $node->getTranslation($code);
      $values = json_encode($translation->toArray(), JSON_PRETTY_PRINT);
      file_put_contents("$directory/node-$nid-$code.json", $values);
      if (!empty($translation->field_article_body)) {
        foreach ($translation->field_article_body as $section) {
          $section = $section->entity;
          $sid = $section->id();
          $values = json_encode($section->toArray(), JSON_PRETTY_PRINT);
          file_put_contents("$directory/section-$sid-$code.json", $values);
        }
      }
      if (!empty($translation->field_landing_contents)) {
        foreach ($translation->field_landing_contents as $section) {
          $section = $section->entity;
          $sid = $section->id();
          $values = json_encode($section->toArray(), JSON_PRETTY_PRINT);
          file_put_contents("$directory/section-$sid-$code.json", $values);
        }
      }
    }
  }
  echo "$nid\n";
}
