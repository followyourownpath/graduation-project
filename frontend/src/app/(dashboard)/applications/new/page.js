'use client';

import { useState } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CloudUpload, File as FileIcon, X, CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from 'next/navigation';

export default function NewApplicationPage() {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Handle Drag Events
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };
  
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = (newFiles) => {
    // Simulate uploading state for each file
    const newFilesWithProgress = newFiles.map(file => ({
      file,
      id: Math.random().toString(36).substring(7),
      progress: 0,
      status: 'uploading' // uploading, completed
    }));
    
    setFiles(prev => [...prev, ...newFilesWithProgress]);

    // Simulate progress animation
    newFilesWithProgress.forEach(fileObj => {
      let currentProgress = 0;
      const interval = setInterval(() => {
        currentProgress += Math.floor(Math.random() * 20) + 10;
        if (currentProgress >= 100) {
          currentProgress = 100;
          clearInterval(interval);
          
          setFiles(current => 
            current.map(f => 
              f.id === fileObj.id ? { ...f, progress: 100, status: 'completed' } : f
            )
          );
        } else {
          setFiles(current => 
            current.map(f => 
              f.id === fileObj.id ? { ...f, progress: currentProgress } : f
            )
          );
        }
      }, 300);
    });
  };

  const removeFile = (id) => {
    setFiles(files.filter(f => f.id !== id));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    // Simulate API call to create application
    setTimeout(() => {
      setIsSubmitting(false);
      router.push('/applications');
    }, 1500);
  };

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">New Application</h1>
        <p className="text-sm text-slate-500 mt-1">Create a new mortgage application and upload supporting documents.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Applicant Details */}
        <Card>
          <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="applicantName">Applicant Full Name</Label>
              <Input id="applicantName" placeholder="e.g. Sarah Jenkins" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="loanType">Loan Type</Label>
              <Select defaultValue="purchase">
                <SelectTrigger>
                  <SelectValue placeholder="Select loan type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="purchase">Purchase (30-Yr Fixed)</SelectItem>
                  <SelectItem value="refinance">Refinance</SelectItem>
                  <SelectItem value="heloc">HELOC</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Drag and Drop Zone */}
        <div 
          className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors
            ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-slate-50 hover:bg-slate-100'}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <CloudUpload className="mx-auto h-16 w-16 text-blue-500 mb-4" />
          <h3 className="text-xl font-semibold text-slate-700 mb-2">
            Drag & Drop Files Here
          </h3>
          <p className="text-slate-500 mb-6">or click to browse your computer</p>
          
          <input 
            type="file" 
            multiple 
            className="hidden" 
            id="file-upload" 
            onChange={handleFileInput}
            accept=".pdf,.jpg,.jpeg,.png,.tiff"
          />
          <Label 
            htmlFor="file-upload" 
            className="cursor-pointer inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background bg-slate-900 text-white hover:bg-slate-900/90 h-10 py-2 px-4"
          >
            Browse Files
          </Label>
          <p className="text-xs text-slate-400 mt-4">Supported formats: PDF, JPEG, PNG, TIFF (Max 25 MB per file)</p>
        </div>

        {/* Attached Files List */}
        {files.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-semibold text-slate-800">Attached Documents ({files.length})</h4>
            <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
              {files.map(fileObj => (
                <div key={fileObj.id} className="p-4 flex items-center justify-between">
                  <div className="flex items-center space-x-4 flex-1">
                    <div className="h-10 w-10 rounded bg-slate-100 flex items-center justify-center text-slate-500">
                      <FileIcon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 max-w-md">
                      <p className="text-sm font-medium text-slate-700 truncate">{fileObj.file.name}</p>
                      <p className="text-xs text-slate-400">{(fileObj.file.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                  </div>
                  
                  <div className="flex-1 px-8">
                    <div className="w-full bg-slate-100 rounded-full h-2 mb-1 overflow-hidden">
                      <div 
                        className={`h-2 rounded-full transition-all duration-300 ease-out ${fileObj.status === 'completed' ? 'bg-emerald-500' : 'bg-blue-600'}`}
                        style={{ width: `${fileObj.progress}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>{fileObj.status === 'completed' ? 'Completed' : 'Uploading...'}</span>
                      <span>{fileObj.progress}%</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4">
                    {fileObj.status === 'completed' ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                    )}
                    <button 
                      type="button" 
                      onClick={() => removeFile(fileObj.id)}
                      className="text-slate-400 hover:text-red-500 transition-colors"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-4 pt-4 border-t border-slate-200">
          <Link href="/applications">
            <Button variant="outline" type="button" disabled={isSubmitting}>Cancel</Button>
          </Link>
          <Button 
            type="submit" 
            className="bg-blue-600 hover:bg-blue-700"
            disabled={isSubmitting || files.length === 0 || files.some(f => f.status !== 'completed')}
          >
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Submit Application
          </Button>
        </div>
      </form>
    </div>
  );
}
