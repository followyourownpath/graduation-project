'use client';

import { useState } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CloudUpload, File as FileIcon, X, CheckCircle2, Loader2, AlertCircle, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useRouter } from 'next/navigation';

// Data Configuration
const LOAN_TYPES = [
  { id: 'purchase', label: 'Owner-Occupier Purchase' },
  { id: 'investment', label: 'Investment Purchase' },
  { id: 'refinance', label: 'Refinance' },
  { id: 'first_home', label: 'First Home Buyer' },
  { id: 'self_employed', label: 'Self-Employed (any)' }
];

const DOCUMENT_REQUIREMENTS = {
  purchase: [
    { id: 'payslip', label: 'Payslip — in 4 weeks', required: true },
    { id: 'bank_statement_3m', label: 'Bank statements — in 3 months', required: true },
    { id: 'id_100', label: '100-pt ID (e.g. passport + licence)', required: true },
    { id: 'contract_of_sale', label: 'Contract of sale', required: true },
    { id: 'property_valuation', label: 'Property valuation', required: true },
  ],
  investment: [
    { id: 'payslip', label: 'Payslip — in 4 weeks', required: true },
    { id: 'bank_statement_3m', label: 'Bank statements — in 3 months', required: true },
    { id: 'id_100', label: '100-pt ID', required: true },
    { id: 'contract_of_sale', label: 'Contract of sale', required: true },
    { id: 'property_valuation', label: 'Property valuation', required: true },
    { id: 'rental_appraisal', label: 'Rental appraisal / lease agreement', required: true },
  ],
  refinance: [
    { id: 'payslip', label: 'Payslip — in 4 weeks', required: true },
    { id: 'bank_statement_3m', label: 'Bank statements — in 3 months', required: true },
    { id: 'id_100', label: '100-pt ID', required: true },
    { id: 'existing_loan_statements', label: 'Existing loan statements — in 6 months', required: true },
    { id: 'property_valuation', label: 'Property valuation', required: true },
  ],
  first_home: [
    { id: 'payslip', label: 'Payslip — in 4 weeks', required: true },
    { id: 'bank_statement_3m', label: 'Bank statements — in 3 months', required: true },
    { id: 'id_100', label: '100-pt ID', required: true },
    { id: 'contract_of_sale', label: 'Contract of sale', required: true },
    { id: 'property_valuation', label: 'Property valuation', required: true },
    { id: 'first_home_grant', label: 'First Home Owner Grant application', required: true },
  ],
  self_employed: [
    { id: 'tax_return', label: 'Tax returns — in 2 years', required: true },
    { id: 'ato_notice', label: 'ATO Notice of Assessment', required: true },
    { id: 'profit_loss', label: 'Profit & Loss statement — accountant-certified', required: true },
    { id: 'bank_statement_3m', label: 'Bank statements — in 3 months', required: true },
    { id: 'id_100', label: '100-pt ID', required: true },
    { id: 'property_valuation', label: 'Property valuation', required: true },
  ]
};

export default function NewApplicationPage() {
  const router = useRouter();
  
  // States
  const [loanType, setLoanType] = useState('purchase');
  const [applicantName, setApplicantName] = useState('');
  const [categoryFiles, setCategoryFiles] = useState({}); // { categoryId: [fileObj, ...] }
  const [isSubmitting, setIsSubmitting] = useState(false);

  const activeRequirements = DOCUMENT_REQUIREMENTS[loanType] || [];

  // Handle Loan Type Change
  const handleLoanTypeChange = (value) => {
    setLoanType(value);
    // Overlapping files are kept intentionally to improve UX when toggling
  };

  // Upload Logic
  const handleFileInput = (e, categoryId) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesForCategory(Array.from(e.target.files), categoryId);
    }
  };

  const handleFilesForCategory = (newFiles, categoryId) => {
    const newFilesWithProgress = newFiles.map(file => ({
      file,
      id: Math.random().toString(36).substring(7),
      progress: 0,
      status: 'uploading', // uploading, processing_ocr, completed
      ocrStatus: 'Pending OCR'
    }));
    
    setCategoryFiles(prev => {
      const existing = prev[categoryId] || [];
      return { ...prev, [categoryId]: [...existing, ...newFilesWithProgress] };
    });

    // Simulate progress and OCR stages
    newFilesWithProgress.forEach(fileObj => {
      let currentProgress = 0;
      const interval = setInterval(() => {
        currentProgress += Math.floor(Math.random() * 30) + 10;
        
        if (currentProgress >= 100) {
          currentProgress = 100;
          clearInterval(interval);
          
          // Move to processing OCR phase
          setCategoryFiles(current => {
            const catFiles = current[categoryId] || [];
            return {
              ...current,
              [categoryId]: catFiles.map(f => 
                f.id === fileObj.id ? { ...f, progress: 100, status: 'processing_ocr', ocrStatus: 'Processing OCR...' } : f
              )
            };
          });

          // Simulate OCR completion
          setTimeout(() => {
            setCategoryFiles(current => {
              const catFiles = current[categoryId] || [];
              return {
                ...current,
                [categoryId]: catFiles.map(f => 
                  f.id === fileObj.id ? { ...f, status: 'completed', ocrStatus: 'Ready' } : f
                )
              };
            });
          }, 1500);

        } else {
          setCategoryFiles(current => {
            const catFiles = current[categoryId] || [];
            return {
              ...current,
              [categoryId]: catFiles.map(f => 
                f.id === fileObj.id ? { ...f, progress: currentProgress } : f
              )
            };
          });
        }
      }, 200);
    });
  };

  const removeFile = (categoryId, fileId) => {
    setCategoryFiles(prev => {
      const updatedFiles = (prev[categoryId] || []).filter(f => f.id !== fileId);
      return { ...prev, [categoryId]: updatedFiles };
    });
  };

  // Validation
  const getMissingCategories = () => {
    return activeRequirements.filter(req => {
      const files = categoryFiles[req.id];
      return req.required && (!files || files.length === 0);
    });
  };
  
  const missingCategories = getMissingCategories();
  const isValid = missingCategories.length === 0 && applicantName.trim() !== '';

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isValid) return;
    
    setIsSubmitting(true);
    // Simulate API call
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
              <Input 
                id="applicantName" 
                placeholder="e.g. Sarah Jenkins" 
                value={applicantName}
                onChange={(e) => setApplicantName(e.target.value)}
                required 
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="loanType">Loan Type</Label>
              <Select value={loanType} onValueChange={handleLoanTypeChange}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select loan type" />
                </SelectTrigger>
                <SelectContent>
                  {LOAN_TYPES.map(type => (
                    <SelectItem key={type.id} value={type.id}>{type.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Dynamic Document Checklist */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-800">Required Documents</h3>
            {missingCategories.length > 0 ? (
              <span className="text-sm font-medium text-amber-600 flex items-center bg-amber-50 px-3 py-1 rounded-full border border-amber-200">
                <AlertCircle className="w-4 h-4 mr-2" />
                Missing {missingCategories.length} required documents
              </span>
            ) : (
              <span className="text-sm font-medium text-emerald-600 flex items-center bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                <CheckCircle2 className="w-4 h-4 mr-2" />
                All requirements met
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4">
            {activeRequirements.map(req => {
              const files = categoryFiles[req.id] || [];
              const isSatisfied = files.length > 0;
              
              return (
                <Card key={req.id} className={`border-l-4 transition-colors ${isSatisfied ? 'border-l-emerald-500' : 'border-l-amber-400'}`}>
                  <CardContent className="p-4 flex flex-col md:flex-row md:items-start justify-between gap-4">
                    
                    {/* Left: Category Info */}
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <h4 className="font-semibold text-slate-800">{req.label}</h4>
                        {req.required && (
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">Required</span>
                        )}
                      </div>
                      
                      {/* Uploaded Files List for this Category */}
                      {files.length > 0 && (
                        <div className="mt-3 space-y-2">
                          {files.map(fileObj => (
                            <div key={fileObj.id} className="bg-slate-50 border border-slate-200 rounded-md p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                              <div className="flex items-center space-x-3 overflow-hidden">
                                <div className="h-8 w-8 rounded bg-white border border-slate-200 flex items-center justify-center text-slate-500 flex-shrink-0">
                                  <FileIcon className="h-4 w-4" />
                                </div>
                                <div className="min-w-0">
                                  <p className="text-sm font-medium text-slate-700 truncate max-w-[150px] sm:max-w-[200px]">{fileObj.file.name}</p>
                                  <p className="text-xs text-slate-400">{(fileObj.file.size / (1024 * 1024)).toFixed(2)} MB</p>
                                </div>
                              </div>
                              
                              <div className="flex-1 w-full sm:px-4 flex items-center space-x-4 mt-2 sm:mt-0">
                                {/* Upload / OCR Progress */}
                                <div className="flex-1">
                                  <div className="w-full bg-slate-200 rounded-full h-1.5 mb-1 overflow-hidden">
                                    <div 
                                      className={`h-1.5 rounded-full transition-all duration-300 ease-out ${
                                        fileObj.status === 'completed' ? 'bg-emerald-500' : 
                                        fileObj.status === 'processing_ocr' ? 'bg-indigo-500' : 'bg-blue-500'
                                      }`}
                                      style={{ width: `${fileObj.progress}%` }}
                                    ></div>
                                  </div>
                                  <div className="flex justify-between text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                                    <span>{fileObj.status === 'uploading' ? 'Uploading' : 'OCR Status'}</span>
                                    <span className={fileObj.status === 'completed' ? 'text-emerald-600' : 'text-blue-600'}>
                                      {fileObj.ocrStatus}
                                    </span>
                                  </div>
                                </div>
                                
                                {/* Status Icon & Remove */}
                                <div className="flex items-center space-x-3 flex-shrink-0">
                                  {fileObj.status === 'completed' ? (
                                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                                  ) : (
                                    <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                                  )}
                                  <button 
                                    type="button" 
                                    onClick={() => removeFile(req.id, fileObj.id)}
                                    className="text-slate-400 hover:text-red-500 transition-colors p-1"
                                  >
                                    <X className="h-4 w-4" />
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    {/* Right: Upload Button */}
                    <div className="flex-shrink-0 flex items-center mt-3 md:mt-0">
                      <input 
                        type="file" 
                        multiple 
                        className="hidden" 
                        id={`file-upload-${req.id}`} 
                        onChange={(e) => handleFileInput(e, req.id)}
                        accept=".pdf,.jpg,.jpeg,.png,.tiff"
                      />
                      <Label 
                        htmlFor={`file-upload-${req.id}`} 
                        className="cursor-pointer inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-slate-300 bg-white hover:bg-slate-50 h-9 px-4 text-slate-700 shadow-sm"
                      >
                        <UploadCloud className="w-4 h-4 mr-2 text-slate-500" />
                        Attach File
                      </Label>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-4 pt-6 border-t border-slate-200">
          <Link href="/applications">
            <Button variant="outline" type="button" disabled={isSubmitting}>Cancel</Button>
          </Link>
          <Button 
            type="submit" 
            className="bg-blue-600 hover:bg-blue-700"
            disabled={isSubmitting || !isValid || Object.values(categoryFiles).flat().some(f => f.status !== 'completed')}
          >
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Submit Application
          </Button>
        </div>
      </form>
    </div>
  );
}
