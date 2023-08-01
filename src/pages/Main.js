import { withAuthenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { useState } from "react";
import { Auth, API, Amplify } from "aws-amplify";
import config from "./../aws-exports.js";
Auth.configure(config);

async function download_file(filename, redacted, filetype) {
  const user = await Auth.currentAuthenticatedUser();
  const token = user.signInUserSession.idToken.jwtToken;
  const requestData = {
    headers: {
      Authorization: "Bearer " + token,
    },
    queryStringParameters: {
      original_filename: filename,
      redacted: redacted,
      filetype: filetype,
    },
  };
  try {
    const data = await API.get("phibyeapi", "/geturl", requestData);
    return data;
  } catch (error) {
    console.log(error);
  }

  return;
}

async function callApiDynamo(filename, date, filetype, redacted) {
  const user = await Auth.currentAuthenticatedUser();
  const token = user.signInUserSession.idToken.jwtToken;

  const requestData = {
    headers: {
      Authorization: "Bearer " + token,
    },
    queryStringParameters: {
      requested_filename: filename,
      upload_date: date,
      filetype: filetype,
      redacted: redacted,
    },
  };
  try {
    const data = await API.get("phibyeapi", "/pulldata", requestData);
    return data;
  } catch (error) {
    console.log(error);
  }
}

function MyForm() {
  const [filename, setfileName] = useState("");
  const [date, setDate] = useState("");
  const [redacted, setRedacted] = useState("");
  const [filetype, setFileType] = useState("");
  const [filetable, setFileTable] = useState([]);

  const handleDownloadClick = (filename, redacted, filetype) => {
    download_file(filename, redacted, filetype).then((response) => {
      window.open(response, "_blank");
    });
  };
  const handleSubmit = (event) => {
    event.preventDefault();
    callApiDynamo(filename, date, filetype, redacted).then((response) => {
      console.log(filetype);
      console.log(redacted);
      /* ACCESS DYNAMODB ITEMS HERE */
      console.log(response);
      setFileTable(response);
    });
  };
  return (
    <div>
      <h1>File Lookup Page</h1>
      <form onSubmit={handleSubmit}>
        <div class="input-group">
          <label class="dialog-box">
            Enter Filename:
            <input
              class="input"
              type="text"
              value={filename}
              onChange={(e) => setfileName(e.target.value)}
            />
          </label>
          <br></br>
          <label class="dialog-box">
            Enter Date:
            <input
              class="input"
              type="Date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          <label class="dialog-box">
            Enter File Type:
            <input
              class="input"
              type="text"
              value={filetype}
              onChange={(e) => setFileType(e.target.value)}
            />
          </label>
          <label class="dialog-box">
            Redacted:
            <input
              class="input"
              type="text"
              value={redacted}
              onChange={(e) => setRedacted(e.target.value)}
            />
          </label>
          <br></br>
        </div>
        <br></br>
        <input className="submit-btn" type="submit" />
      </form>
      <br></br>
      <div className="app-container">
        <table>
          <thead>
            <tr>
              <th>File Name</th>
              <th>File Type</th>
              <th>Redacted</th>
              <th>Upload Date</th>
              <th>Action </th>
            </tr>
          </thead>
          <tbody>
            {filetable.map((fileinfo) => (
              <tr>
                <td>{fileinfo.original_filename}</td>
                <td>{fileinfo.filetype}</td>
                <td>{String(fileinfo.redacted)}</td>
                <td>{fileinfo.upload_date}</td>
                <td>
                  <button
                    onClick={() =>
                      handleDownloadClick(
                        fileinfo.original_filename,
                        String(fileinfo.redacted),
                        fileinfo.filetype
                      )
                    }
                  >
                    Download
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default withAuthenticator(MyForm);
