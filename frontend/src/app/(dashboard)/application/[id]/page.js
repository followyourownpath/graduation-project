'use client';

import { useState, useEffect, use } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CheckCircle, Save, XCircle, Loader2, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from '@/lib/api';
import { toast } from "sonner";
import { formatRiskScoreBadge, riskDisplay } from "@/lib/risk-display";

export default function ApplicationReviewPage({ params }) {
  const unwrappedParams = use(params);
  const appId = unwrappedParams.id;

  const [submission, setSubmission] = useState(null);
  const [activeDocId, setActiveDocId] = useState('');
  const [ocrData, setOcrData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [retryingSync, setRetryingSync] = useState(false);
  const router = useRouter();
  
  // Track edited values
  const [editedFields, setEditedFields] = useState({});

  useEffect(() => {
    const fetchSubmission = async () => {
      try {
        const data = await api.getSubmission(appId);
        setSubmission(data);
        if (data.documents?.length > 0) {
          setActiveDocId(data.documents[0].doc_id);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchSubmission();
  }, [appId]);

  useEffect(() => {
    if (!activeDocId) return;
    const fetchOCR = async () => {
      try {
        setOcrData(null);
        const data = await api.getExtractedData(activeDocId);
        setOcrData(data);
        setEditedFields({}); // Reset edits on tab switch
      } catch (e) {
        console.error(e);
      }
    };
    fetchOCR();
  }, [activeDocId]);

  // Polling logic for CRM Sync and pending OCR
  useEffect(() => {
    if (!submission) return;
    const hasPendingOcr = submission.documents?.some(
      d => d.processing_status !== 'completed' && d.processing_status !== 'failed'
    );
    const hasPendingCrm = submission.submission_status === 'approved' && 
      (submission.crm_sync_status === 'pending' || submission.crm_sync_status === 'in_progress');

    if (!hasPendingOcr && !hasPendingCrm) return;

    const timer = setInterval(async () => {
      try {
        const data = await api.getSubmission(appId);
        setSubmission(data);
        const stillPendingOcr = data.documents?.some(
          d => d.processing_status !== 'completed' && d.processing_status !== 'failed'
        );
        const stillPendingCrm = data.submission_status === 'approved' && 
          (data.crm_sync_status === 'pending' || data.crm_sync_status === 'in_progress');

        if (!stillPendingOcr && !stillPendingCrm) {
          clearInterval(timer);
          if (activeDocId) {
            const ocr = await api.getExtractedData(activeDocId);
            setOcrData(ocr);
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 3000);

    return () => clearInterval(timer);
  }, [submission, appId, activeDocId]);

  const handleFieldChange = (fieldId, newValue, rawValue) => {
    setEditedFields(prev => ({
      ...prev,
      [fieldId]: {
        value: newValue,
        isEdited: newValue !== rawValue
      }
    }));
  };

  const handleSaveCorrections = async () => {
    setSaving(true);
    try {
      const editsToSave = Object.entries(editedFields)
        .filter(([_, data]) => data.isEdited)
        .map(([id, data]) => ({
          id,
          corrected_value: data.value,
          review_status: 'corrected',
          review_notes: 'Manual correction'
        }));

      for (const edit of editsToSave) {
        await api.saveFieldReview(edit.id, edit);
      }
      
      // Fetch latest OCR data to reflect updates immediately
      const updatedOcr = await api.getExtractedData(activeDocId);
      setOcrData(updatedOcr);
      
      // Update local state to clear edits
      setEditedFields({});
      // Reset edit state
      setEditedFields({});
    } catch (error) {
      console.error(error);
      toast.error("Failed to save corrections.");
    } finally {
      setSaving(false);
    }
  };

  const handleStatusUpdate = async (status) => {
    setUpdatingStatus(true);
    try {
      await api.updateSubmissionStatus(appId, status);
      toast.success(`Application ${status} successfully.`);
      if (status === 'approved') {
        const data = await api.getSubmission(appId);
        setSubmission(data);
      } else {
        router.push('/applications');
      }
    } catch (error) {
      console.error(error);
      toast.error(`Failed to ${status} application.`);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleRetrySync = async () => {
    setRetryingSync(true);
    try {
      await api.retryCrmSync(appId);
      toast.success("CRM sync task queued for retry.");
      const data = await api.getSubmission(appId);
      setSubmission(data);
    } catch (error) {
      console.error(error);
      toast.error("Failed to retry CRM sync.");
    } finally {
      setRetryingSync(false);
    }
  };

  if (loading) {
    return <div className="h-full flex items-center justify-center"><Loader2 className="animate-spin text-blue-500 w-8 h-8" /></div>;
  }

  if (!submission) {
    return <div className="p-8">Submission not found.</div>;
  }

  const activeDoc = submission.documents?.find(d => d.doc_id === activeDocId);
  const riskBadge = formatRiskScoreBadge(submission);
  const risk = riskDisplay(submission.risk_level);

  // Group fields by section and ensure deterministic sorting
  const groupedFields = ocrData?.fields?.slice()
    .sort((a, b) => (a.field_key || '').localeCompare(b.field_key || ''))
    .reduce((acc, field) => {
    const section = field.section_name || 'General';
    (acc[section] = acc[section] || []).push(field);
    return acc;
  }, {}) || {};

  return (
    <div className="h-full flex overflow-hidden">
      {/* Left Pane - Document Viewer */}
      <div className="w-1/2 border-r border-slate-200 bg-slate-100 flex flex-col">
        <div className="p-4 border-b border-slate-200 bg-white flex justify-between items-center">
          <Tabs value={activeDocId} onValueChange={setActiveDocId} className="w-full">
            <TabsList className="w-full justify-start overflow-x-auto">
              {submission.documents?.map(doc => (
                <TabsTrigger key={doc.doc_id} value={doc.doc_id} className="flex items-center gap-2">
                  {doc.document_type}
                  {doc.processing_status !== 'completed' && doc.processing_status !== 'failed' && (
                    <Loader2 className="h-3 w-3 animate-spin text-slate-400" />
                  )}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
        <div className="flex-1 overflow-hidden relative bg-slate-200/50">
          {activeDoc?.storage_uri ? (
            <iframe 
              src={activeDoc.storage_uri} 
              className="w-full h-full border-0" 
              title="Document Preview"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-slate-400">
              <div className="text-center">
                <div className="w-64 h-80 bg-white shadow-lg border border-slate-200 flex flex-col items-center justify-center p-6 mx-auto mb-4 rounded-sm">
                  {activeDoc?.processing_status === 'processing' ? (
                    <>
                      <Loader2 className="h-16 w-16 text-blue-500 animate-spin mb-4" />
                      <p className="text-sm font-medium text-slate-500">Processing OCR...</p>
                    </>
                  ) : (
                    <>
                      <FileIcon className="h-16 w-16 text-slate-300 mb-4" />
                      <p className="text-sm font-medium text-slate-500">Document preview unavailable</p>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Pane - OCR Data & Review Panel */}
      <div className="w-1/2 flex flex-col bg-white overflow-hidden">
        <ScrollArea className="flex-1 min-h-0 h-full p-6">
          <div className="space-y-8 pb-12">
            
            {/* Header info */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h2 className="text-xl font-bold text-slate-900">Application Review</h2>
                  <Badge variant="outline" className={`${riskBadge.className} font-medium`}>
                    {riskBadge.scoreText != null
                      ? `Risk: ${riskBadge.scoreText} (${risk.label})`
                      : riskBadge.label}
                  </Badge>
                  {submission.assessment_status === "completed" && (
                    <Link href={`/rules-engine/${appId}`}>
                      <Button type="button" variant="outline" size="sm" className="h-7">
                        <ShieldAlert className="mr-1.5 h-3.5 w-3.5" />
                        View Risk Report
                      </Button>
                    </Link>
                  )}
                </div>
                <Badge variant="secondary" className="w-fit text-xs px-2.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 font-medium">
                  Source: {submission.source_channel === 'crm' ? 'Mercury CRM Channel' : 'Manual Intake Channel'}
                </Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-slate-200/80 text-xs">
                <div>
                  <span className="text-slate-400 block mb-1 font-medium">Applicant Name</span>
                  <span className="font-semibold text-slate-800 text-sm">{submission.customer_name}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1 font-medium">Local Application ID (SmartFINN)</span>
                  <span className="font-mono font-medium text-slate-700 bg-white px-2 py-1 rounded border border-slate-200 block truncate shadow-2xs" title={submission.local_application_id || appId}>
                    {submission.local_application_id || appId}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1 font-medium">Mercury CRM External ID</span>
                  {submission.crm_sync_status === 'completed' && submission.crm_application_id ? (
                    <span className="font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-1 rounded border border-emerald-200 flex items-center gap-1.5 shadow-2xs w-fit" title={submission.crm_application_id}>
                      <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
                      {submission.crm_application_id}
                    </span>
                  ) : submission.crm_sync_status === 'in_progress' ? (
                    <span className="font-mono text-blue-700 bg-blue-50 px-2 py-1 rounded border border-blue-200 flex items-center gap-1.5 shadow-2xs w-fit">
                      <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                      Syncing (In Progress)...
                    </span>
                  ) : submission.crm_sync_status === 'pending' ? (
                    <span className="font-mono text-amber-700 bg-amber-50 px-2 py-1 rounded border border-amber-200 flex items-center gap-1.5 shadow-2xs w-fit">
                      <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                      Syncing (Queued)...
                    </span>
                  ) : submission.crm_sync_status === 'failed' || submission.crm_sync_status === 'failed_permanent' ? (
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-red-700 bg-red-50 px-2 py-1 rounded border border-red-200 flex items-center gap-1.5 shadow-2xs w-fit">
                        <span className="inline-block w-2 h-2 rounded-full bg-red-500"></span>
                        Sync Failed
                      </span>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 px-2 text-xs border-red-200 hover:bg-red-50 text-red-700 font-medium"
                        onClick={handleRetrySync}
                        disabled={retryingSync}
                      >
                        {retryingSync ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1 text-red-500" /> : null}
                        Retry
                      </Button>
                    </div>
                  ) : (
                    <span className="font-mono text-slate-400 bg-slate-100/80 px-2 py-1 rounded border border-slate-200 block italic">
                      Pending Sync (Unmapped)
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* OCR Extracted Data Form */}
            {ocrData ? (
              <Card>
                <CardHeader>
                  <CardTitle>Extracted Data ({ocrData.document_type})</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {Object.entries(groupedFields).map(([section, fields]) => (
                    <div key={section} className="space-y-4">
                      <h4 className="text-sm font-semibold text-slate-500 uppercase border-b pb-1">
                        {section}
                      </h4>
                      <div className="grid grid-cols-2 gap-4">
                        {fields.map(field => {
                          const isEdited = editedFields[field.field_id]?.isEdited;
                          const currentValue = editedFields[field.field_id]?.value ?? field.raw_value;
                          const isLowConfidence = field.confidence < 0.8;
                          
                          return (
                            <div key={field.field_id} className="space-y-2">
                              <Label className="flex items-center flex-wrap gap-2">
                                {field.field_label}
                                {isLowConfidence && (
                                  <span className="text-[10px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-medium">
                                    Low: {Math.round(field.confidence * 100)}%
                                  </span>
                                )}
                                {isEdited && (
                                  <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium">
                                    Edited
                                  </span>
                                )}
                              </Label>
                              <Input 
                                value={currentValue}
                                onChange={(e) => handleFieldChange(field.field_id, e.target.value, field.raw_value)}
                                className={isLowConfidence && !isEdited ? 'border-red-300 focus-visible:ring-red-500' : ''} 
                              />
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                  
                  {ocrData.fields?.length > 0 && (
                    <div className="flex justify-end pt-4 border-t">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={handleSaveCorrections}
                        disabled={saving || !Object.values(editedFields).some(f => f.isEdited)}
                      >
                        {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                        Save Corrections
                      </Button>
                    </div>
                  )}
                  {ocrData.fields?.length === 0 && (
                    <div className="text-center text-slate-500 py-4 text-sm">No data extracted for this document.</div>
                  )}
                </CardContent>
              </Card>
            ) : (
               <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                 {activeDoc?.processing_status === 'processing' ? (
                   <>
                    <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-2" />
                    <p>Loading OCR Data...</p>
                   </>
                 ) : (
                   <p>Select a document to view data</p>
                 )}
               </div>
            )}

          </div>
        </ScrollArea>

        {/* Bottom Action Bar */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-between items-center">
          <Button variant="outline" className="text-slate-600" onClick={() => router.push('/applications')}>
            Cancel Review
          </Button>
          <div className="space-x-3">
            <Button 
              variant="destructive"
              disabled={updatingStatus}
              onClick={() => handleStatusUpdate('rejected')}
            >
              {updatingStatus ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <XCircle className="h-4 w-4 mr-2" />}
              Reject
            </Button>
            <Button 
              className="bg-emerald-600 hover:bg-emerald-700"
              disabled={updatingStatus}
              onClick={() => handleStatusUpdate('approved')}
            >
              {updatingStatus ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle className="h-4 w-4 mr-2" />}
              Approve
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function FileIcon(props) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}
