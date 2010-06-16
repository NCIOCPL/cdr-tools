/*
 * $Id$
 *
 * One-off report for Sheri on protocols with clues about gender in
 * the PatientCharacteristics block.
 *
 * Sheri:
 * "For InScopeProtocol documents, we need the CDR ID and Titles for Active,
 * Approved not yet active, Temporarily closed and Closed trials that have NCT
 * ID's and any of the following words in <PatientCharacteristics>
 *
 *  Male
 *  Female
 *  Women
 *  Men"
 *
 * Lakshmi [comment #1]:
 * "I would drop the status criteria. Just use the NCTID criteria - ie trials
 * that have OtherIDType of ClinicalTrials.gov ID."
 *
 * BZIssue::2830
 */

using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Data;
using System.Data.SqlClient;
using System.Collections;

public class Request2830 {

    public static void Main() {
        string[] targets  = { "male", "female", "men", "women" };
        string choices    = String.Join("|", targets);
        string elemName   = "PatientCharacteristics";
        string expression = String.Format("<{0}.*?\\W({1})\\W.*?</{2}>",
                                          elemName, choices, elemName);
        Regex regex = new Regex(expression,
                                RegexOptions.IgnoreCase |
                                RegexOptions.Singleline);
        StringBuilder sb = new StringBuilder(@"
<html>
 <head>
  <meta http-equiv='Content-Type' content='text/html; charset=utf-8' />
  <title>Protocols with Gender Clues</title>
  <style type='text/css'>
   body   { font-family: Arial; }
   h1     { font-size: 14pt; }
   td, th { font-size: 10pt; }
   td     { vertical-align: top; }
  </style>
 </head>
 <body>
  <h1>Protocols with Gender Clues</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>Doc Title</th>
   </tr>
");
        SqlConnection conn = Cdr.Client.dbConnect("CdrGuest");
        SqlCommand cmd = new SqlCommand(@"
            SELECT DISTINCT doc_id
              FROM query_term
             WHERE path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
	           AND value = 'ClinicalTrials.gov ID'
          ORDER BY doc_id", conn);
        cmd.CommandTimeout = 300;
        SqlDataReader reader = cmd.ExecuteReader();
        ArrayList docIds = new ArrayList();
        while (reader.Read())
            docIds.Add(reader[0]);
        Console.WriteLine("{0} doc ids collected", docIds.Count);
        reader.Close();
        cmd = new SqlCommand(@"
            SELECT title, xml
              FROM document
             WHERE id = @docId", conn);
        cmd.CommandTimeout = 300;
        cmd.Parameters.Add("@docId", SqlDbType.Int);
        int n = 0;
        foreach (int docId in docIds) {
            cmd.Parameters[0].Value = docId;
            reader = cmd.ExecuteReader();
            while (reader.Read()) {
                string title = (string)reader[0];
                string xml   = (string)reader[1];
                Console.Write("\rprocessed {0} documents", ++n);
                if (regex.IsMatch(xml)) {
                    sb.AppendFormat(@"
   <tr>
    <td>{0}</td>
    <td>{1}</td>
   </tr>
", docId, Cdr.Client.escapeXml(title));
                }
            }
            reader.Close();
        }
        sb.Append(@"
  </table>
 </body>
</html>
");
        Stream fs = new FileStream("Request2830.html", FileMode.Create);
        StreamWriter sw = new StreamWriter(fs, Encoding.UTF8);
        sw.Write(sb.ToString());
        sw.Close();
        reader.Close();
        conn.Close();
    }
}
