"use client";

import { useCallback, useState } from "react";
import { Video, Image as ImageIcon, Mail, Globe, FileText, Upload } from "lucide-react";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  accept?: string;
  mediaType?: string;
}

export default function UploadZone({
  onFileSelected,
  accept = "*",
  mediaType,
}: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        setSelectedFile(file);
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setSelectedFile(file);
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const getIcon = (type: string | undefined, isUpload = false) => {
    const size = isUpload ? 36 : 28;
    switch (type) {
      case "video":
        return <Video size={size} className="icon-blue" />;
      case "image":
        return <ImageIcon size={size} className="icon-purple" />;
      case "email":
        return <Mail size={size} className="icon-amber" />;
      case "website":
        return <Globe size={size} className="icon-cyan" />;
      default:
        return isUpload ? (
          <Upload size={size} className="icon-purple" />
        ) : (
          <FileText size={size} className="icon-cyan" />
        );
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      className={`upload-zone ${isDragOver ? "drag-over" : ""} ${selectedFile ? "has-file" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {selectedFile ? (
        <div className="upload-selected">
          <div className="upload-file-icon" style={{ display: "flex", alignItems: "center" }}>
            {getIcon(mediaType)}
          </div>
          <div className="upload-file-info">
            <div className="upload-file-name">{selectedFile.name}</div>
            <div className="upload-file-size">{formatSize(selectedFile.size)}</div>
          </div>
          <button
            className="upload-change-btn"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedFile(null);
            }}
          >
            Change
          </button>
        </div>
      ) : (
        <label className="upload-label">
          <input
            type="file"
            accept={accept}
            onChange={handleFileInput}
            className="upload-input"
          />
          <div className="upload-icon" style={{ display: "flex", alignItems: "center" }}>
            {getIcon(mediaType, true)}
          </div>
          <div className="upload-text">
            <span className="upload-primary">
              Drop your file here or <span className="upload-browse">browse</span>
            </span>
            <span className="upload-secondary">
              {mediaType === "video" && "MP4, AVI, MOV, MKV, WebM"}
              {mediaType === "image" && "JPG, PNG, GIF, WebP, BMP"}
              {mediaType === "email" && ".eml or .msg files"}
              {!mediaType && "Any supported media file"}
            </span>
          </div>
        </label>
      )}
    </div>
  );
}
