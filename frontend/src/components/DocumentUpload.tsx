import { useState } from "react";
import { uploadDocument } from "../api/client";

export function DocumentUpload() {
  const [message, setMessage] = useState("");

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const result = await uploadDocument(file);
    setMessage(`Uploaded ${result.filename}`);
  };

  return (
    <div>
      <input type="file" accept=".txt" onChange={handleUpload} />
      <p>{message}</p>
    </div>
  );
}
