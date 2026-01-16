import React from "react";

type Props = {
  text: string;
};

const SubtitleBox: React.FC<Props> = ({ text }) => {
  return (
    <div
      style={{
        backgroundColor: "#000",
        color: "#fff",
        padding: "24px",
        fontSize: "2rem",
        width: "100%",
        minHeight: "120px",
        textAlign: "center",
        borderRadius: "8px",
        overflowWrap: "break-word",
      }}
    >
      {text || "Waiting for speech..."}
    </div>
  );
};

export default SubtitleBox;
