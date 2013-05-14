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
 * Modified version requested by Lakshmi:
 *
 * "Could you create another flavor of the report - as a 2830_revised. 
 * Look for the values specified below as follows
 *  Sex:
 *    Female
 *
 * Also, after the report is done, could you deduplicate the CDRIDs with the
 * CDRIDS in the EXCEL file attached to issue 2713."
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
using System.Collections.Specialized;
using System.Xml;

public class Request2830 {

    private static void loadDone(string filename, StringCollection done) {
        XmlDocument doc = new XmlDocument();
        XmlTextReader reader = new XmlTextReader(filename);
        doc.Load(reader);
        foreach (XmlNode sheet in doc.DocumentElement.ChildNodes) {
            if (sheet.Name == "Sheet") {
                foreach (XmlNode row in sheet.ChildNodes) {
                    if (row.Name == "Row") {
                        XmlElement rowElem = (XmlElement)row;
                        string num = rowElem.GetAttribute("number");
                        if (num != "0") {
                            foreach (XmlNode col in row.ChildNodes) {
                                if (col.Name == "Col") {
                                    XmlElement colElem = (XmlElement)col;
                                    string n = colElem.GetAttribute("number");
                                    if (n == "0")
                                        done.Add(col.InnerText);
                                }
                            }
                        }
                    }
                }
                break;
            }
        }
        Console.WriteLine("{0} already done", done.Count);
    }
    public static void Main(string[] argv) {
        StringCollection done = new StringCollection();
        if (argv.Length > 0)
            loadDone(argv[0], done);
        string[] targets  = { "male", "female", "men", "women" };
        string choices    = String.Join("|", targets);
        string elemName   = "PatientCharacteristics";
        string sex        = "\\Wsex\\W";
        string expression = String.Format("<{0}.*?{1}.*?\\W({2})\\W.*?</{3}>",
                                          elemName, sex, choices, elemName);
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
        while (reader.Read()) {
            int docId = (int)reader[0];
            if (!done.Contains(docId.ToString()))
                docIds.Add(docId);
        }
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
                // Console.WriteLine("{0}: {1}", docId, title);
                // Console.Write(".");
                if (regex.IsMatch(xml)) {
                    //Console.Write("!");
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
        Stream fs = new FileStream("Request2830_revised.html",
                                   FileMode.Create);
        StreamWriter sw = new StreamWriter(fs, Encoding.UTF8);
        sw.Write(sb.ToString());
        sw.Close();
        reader.Close();
        conn.Close();
    }
}
