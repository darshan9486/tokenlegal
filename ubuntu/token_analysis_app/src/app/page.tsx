"use client";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Progress } from "../components/ui/progress";
import ResultsTable from "./ResultsTable"; // Import the new table component
import React, { useState, useEffect } from 'react';

export default function HomePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [urlInput, setUrlInput] = useState<string>("");
  const [urls, setUrls] = useState<string[]>([]);
  const [tokenName, setTokenName] = useState<string>("");
  const [tokenSymbol, setTokenSymbol] = useState<string>("");
  const [tokenTypeMethodology, setTokenTypeMethodology] = useState<string>("");
  const [additionalContext, setAdditionalContext] = useState<string>("");
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [viewMode, setViewMode] = useState<"json" | "table">("json"); // To toggle between JSON and Table

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setFiles(Array.from(event.target.files));
    }
  };

  const handleAddUrl = () => {
    if (urlInput && !urls.includes(urlInput)) {
      setUrls([...urls, urlInput]);
      setUrlInput("");
    }
  };

  const handleRemoveUrl = (url: string) => {
    setUrls(urls.filter(u => u !== url));
  };

  const handleRemoveFile = (fileName: string) => {
    setFiles(files.filter(f => f.name !== fileName));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setAnalysisResult(null);
    setProgress(0);

    const formData = new FormData();
    files.forEach(file => formData.append("files", file));
    urls.forEach(url => formData.append("urls", url));
    formData.append("token_name", tokenName);
    formData.append("token_symbol", tokenSymbol);
    formData.append("token_type_methodology", tokenTypeMethodology);
    formData.append("additional_context", additionalContext);

    try {
      // Simulate progress for the upload/processing
      let currentProgress = 0;
      const progressInterval = setInterval(() => {
        currentProgress += 10;
        if (currentProgress <= 100) {
          setProgress(currentProgress);
        } else {
          clearInterval(progressInterval);
        }
      }, 200);

      const response = await fetch("http://localhost:8000/analyze/", {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setAnalysisResult(data);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
      setProgress(0); // Reset progress bar
    }
  };

  const handleExportJson = () => {
    if (!analysisResult) return;
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(analysisResult, null, 2)
    )}`;
    const link = document.createElement("a");
    link.href = jsonString;
    link.download = `${tokenSymbol || tokenName || "analysis"}_export.json`;
    link.click();
  };

  const flattenObject = (obj: any, prefix = "", res: any = {}) => {
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        const newKey = prefix ? prefix + "." + key : key;
        if (typeof obj[key] === "object" && obj[key] !== null && !Array.isArray(obj[key])) {
          flattenObject(obj[key], newKey, res);
        } else if (Array.isArray(obj[key])) {
          // Attempt to make arrays more CSV-friendly, e.g., by joining simple values
          // or by creating multiple rows/columns if complex (more advanced)
          res[newKey] = obj[key].map((item: any) => typeof item === 'object' ? JSON.stringify(item) : item).join("; ");
        } else {
          res[newKey] = obj[key];
        }
      }
    }
    return res;
  };

  const convertToCSV = (jsonData: any) => {
    const flatData = flattenObject(jsonData);
    const headers = Object.keys(flatData).join(",");
    const values = Object.values(flatData).map(value => {
      const strValue = String(value);
      // Escape commas and quotes in values
      return `"${strValue.replace(/"/g, '""')}"`;
    }).join(",");
    return `${headers}\n${values}`;
  };

  const handleExportCsv = () => {
    if (!analysisResult) return;
    const csvString = convertToCSV(analysisResult);
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `${tokenSymbol || tokenName || "analysis"}_export.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };


  return (
    <div className="container mx-auto p-4 md:p-8 bg-gray-900 text-gray-100 min-h-screen">
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-center text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
          Token Analysis Engine
        </h1>
      </header>

      <form onSubmit={handleSubmit} className="space-y-6 bg-gray-800 p-6 rounded-lg shadow-xl mb-8">
        <div>
          <Label htmlFor="file-upload" className="block text-sm font-medium text-gray-300 mb-1">Upload PDF Documents</Label>
          <Input id="file-upload" type="file" multiple onChange={handleFileChange} className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-purple-600 file:text-white hover:file:bg-purple-700" />
        </div>
        <div className="mb-2">
          <div className="text-gray-400 mb-1">Selected files:</div>
          {files.length === 0 && <div className="text-gray-500 text-sm">No files selected.</div>}
          {files.map((file) => (
            <div key={file.name} className="flex items-center text-sm text-gray-200 mb-1">
              <span>{file.name}</span>
              <button type="button" onClick={() => handleRemoveFile(file.name)} style={{ marginLeft: 8, color: '#f87171', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
            </div>
          ))}
        </div>
        <div className="mb-2">
          <div className="text-gray-400 mb-1">Add Document URLs</div>
          <div className="flex gap-2">
            <Input type="url" value={urlInput} onChange={e => setUrlInput(e.target.value)} placeholder="https://example.com/document.pdf" />
            <Button type="button" onClick={handleAddUrl}>Add URL</Button>
          </div>
          {urls.length > 0 && (
            <div className="mt-2">
              {urls.map(url => (
                <div key={url} className="flex items-center text-sm text-gray-200 mb-1">
                  <span>{url}</span>
                  <button type="button" onClick={() => handleRemoveUrl(url)} style={{ marginLeft: 8, color: '#f87171', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="tokenName" className="block text-sm font-medium text-gray-300 mb-1">Token Name</Label>
            <Input id="tokenName" type="text" value={tokenName} onChange={(e) => setTokenName(e.target.value)} placeholder="e.g., Ethena USDe" className="w-full p-2 border border-gray-600 rounded-md bg-gray-700 text-gray-200 focus:ring-purple-500 focus:border-purple-500" />
          </div>
          <div>
            <Label htmlFor="tokenSymbol" className="block text-sm font-medium text-gray-300 mb-1">Token Symbol</Label>
            <Input id="tokenSymbol" type="text" value={tokenSymbol} onChange={(e) => setTokenSymbol(e.target.value)} placeholder="e.g., USDe" className="w-full p-2 border border-gray-600 rounded-md bg-gray-700 text-gray-200 focus:ring-purple-500 focus:border-purple-500" />
          </div>
        </div>
        <div>
          <Label htmlFor="tokenTypeMethodology" className="block text-sm font-medium text-gray-300 mb-1">Token Type/Methodology</Label>
          <Input id="tokenTypeMethodology" type="text" value={tokenTypeMethodology} onChange={(e) => setTokenTypeMethodology(e.target.value)} placeholder="e.g., Fiat-backed Stablecoin" className="w-full p-2 border border-gray-600 rounded-md bg-gray-700 text-gray-200 focus:ring-purple-500 focus:border-purple-500" />
        </div>
        <div>
          <Label htmlFor="additionalContext" className="block text-sm font-medium text-gray-300 mb-1">Additional Context (Optional)</Label>
          <Textarea id="additionalContext" value={additionalContext} onChange={(e) => setAdditionalContext(e.target.value)} placeholder="Provide any other relevant information or specific questions..." className="w-full p-2 border border-gray-600 rounded-md bg-gray-700 text-gray-200 focus:ring-purple-500 focus:border-purple-500" rows={3} />
        </div>
        <Button type="submit" disabled={isLoading || (files.length === 0 && urls.length === 0)} className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold py-2 px-4 rounded-md disabled:opacity-50">
          {isLoading ? "Analyzing..." : "Analyze Tokens"}
        </Button>
      </form>

      {isLoading && (
        <div className="w-full bg-gray-700 rounded-full h-2.5 mb-4">
          <Progress value={progress} className="h-2.5 rounded-full bg-purple-600" />
        </div>
      )}

      {error && (
        <div className="bg-red-800 border border-red-700 text-red-200 px-4 py-3 rounded-md relative mb-6" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {analysisResult && (
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">Analysis Results</h2>
            <div className="space-x-2">
              <Button onClick={() => setViewMode("json")} variant={viewMode === 'json' ? 'default' : 'outline'} className={`${viewMode === 'json' ? 'bg-purple-600 hover:bg-purple-700' : 'border-purple-600 text-purple-400 hover:bg-purple-900 hover:text-purple-300'}`}>JSON</Button>
              <Button onClick={() => setViewMode("table")} variant={viewMode === 'table' ? 'default' : 'outline'} className={`${viewMode === 'table' ? 'bg-purple-600 hover:bg-purple-700' : 'border-purple-600 text-purple-400 hover:bg-purple-900 hover:text-purple-300'}`}>Table</Button>
            </div>
          </div>
          
          {viewMode === "json" ? (
            <pre className="bg-gray-900 p-4 rounded-md overflow-x-auto text-sm whitespace-pre-wrap break-all">
              {JSON.stringify(analysisResult, null, 2)}
            </pre>
          ) : (
            <ResultsTable data={analysisResult} />
          )}

          <div className="mt-6 flex space-x-3">
            <Button onClick={handleExportJson} className="bg-green-600 hover:bg-green-700 text-white">Export JSON</Button>
            <Button onClick={handleExportCsv} className="bg-blue-600 hover:bg-blue-700 text-white">Export CSV</Button>
          </div>
        </div>
      )}
    </div>
  );
}

