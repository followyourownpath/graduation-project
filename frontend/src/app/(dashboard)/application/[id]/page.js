import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AlertTriangle, CheckCircle, Save, XCircle } from "lucide-react";

export default function ApplicationReviewPage({ params }) {
  // Normally fetch data using params.id
  const appId = params.id;

  return (
    <div className="h-full flex overflow-hidden">
      {/* Left Pane - Document Viewer */}
      <div className="w-1/2 border-r border-slate-200 bg-slate-100 flex flex-col">
        <div className="p-4 border-b border-slate-200 bg-white flex justify-between items-center">
          <Tabs defaultValue="payslip" className="w-[400px]">
            <TabsList>
              <TabsTrigger value="payslip">Payslip (Aug 2023)</TabsTrigger>
              <TabsTrigger value="id">Passport</TabsTrigger>
              <TabsTrigger value="bank">Bank Statement</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        <div className="flex-1 p-8 overflow-auto flex items-center justify-center relative">
          <div className="absolute inset-0 flex items-center justify-center text-slate-400">
            {/* Placeholder for PDF Viewer */}
            <div className="text-center">
              <div className="w-64 h-80 bg-white shadow-lg border border-slate-200 flex flex-col items-center justify-center p-6 mx-auto mb-4">
                <FileIcon className="h-16 w-16 text-slate-300 mb-4" />
                <p className="text-sm font-medium text-slate-500">Document rendering preview...</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Pane - OCR Data & Review Panel */}
      <div className="w-1/2 flex flex-col bg-white">
        <ScrollArea className="flex-1 p-6">
          <div className="space-y-8">
            
            {/* Header info */}
            <div>
              <div className="flex items-center space-x-3 mb-2">
                <h2 className="text-2xl font-bold">Review: {appId}</h2>
                <Badge variant="outline" className="border-red-500 text-red-700 bg-red-50">
                  Risk Score: 85 (High)
                </Badge>
              </div>
              <p className="text-sm text-slate-500">Applicant: Alice Smith • Submitted: 2026-06-25</p>
            </div>

            {/* Alerts Panel */}
            <Card className="border-red-200 bg-red-50/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-red-700 flex items-center text-lg">
                  <AlertTriangle className="h-5 w-5 mr-2" />
                  Compliance Alerts (2)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 bg-white border border-red-200 rounded-md">
                  <p className="text-sm font-medium text-red-800">Income Discrepancy</p>
                  <p className="text-sm text-slate-600 mt-1">
                    Declared income ($8,500) does not match extracted payslip income ($7,200).
                  </p>
                  <div className="mt-3 flex space-x-2">
                    <Button size="sm" variant="outline" className="text-xs">Add Note</Button>
                    <Button size="sm" variant="ghost" className="text-xs text-red-600 hover:text-red-700 hover:bg-red-50">Mark Resolved</Button>
                  </div>
                </div>
                <div className="p-3 bg-white border border-amber-200 rounded-md">
                  <p className="text-sm font-medium text-amber-800">Recent Employment Change</p>
                  <p className="text-sm text-slate-600 mt-1">
                    Applicant has been with current employer for less than 3 months.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* OCR Extracted Data Form */}
            <Card>
              <CardHeader>
                <CardTitle>Extracted Data (Payslip)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Employer Name</Label>
                    <Input defaultValue="Tech Corp Inc." />
                  </div>
                  <div className="space-y-2">
                    <Label>Employee Name</Label>
                    <Input defaultValue="Alice Smith" />
                  </div>
                  <div className="space-y-2">
                    <Label>Net Pay</Label>
                    <Input defaultValue="$7,200.00" className="border-red-300 focus-visible:ring-red-500" />
                  </div>
                  <div className="space-y-2">
                    <Label>Pay Period</Label>
                    <Input defaultValue="Aug 01 - Aug 31, 2023" />
                  </div>
                </div>
                <div className="flex justify-end pt-4">
                  <Button variant="outline" size="sm">
                    <Save className="h-4 w-4 mr-2" />
                    Save Corrections
                  </Button>
                </div>
              </CardContent>
            </Card>

          </div>
        </ScrollArea>

        {/* Bottom Action Bar */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-between items-center">
          <Button variant="outline" className="text-slate-600">Cancel Review</Button>
          <div className="space-x-3">
            <Button variant="destructive">
              <XCircle className="h-4 w-4 mr-2" />
              Reject
            </Button>
            <Button className="bg-emerald-600 hover:bg-emerald-700">
              <CheckCircle className="h-4 w-4 mr-2" />
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
