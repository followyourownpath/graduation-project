import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, Clock, AlertTriangle, CheckCircle, ArrowRight } from "lucide-react";
import Link from "next/link";

const mockApplications = [
  { id: 'APP-2026-001', name: 'Alice Smith', type: 'Purchase', date: '2026-06-25', status: 'Pending', risk: 'High', score: 85 },
  { id: 'APP-2026-002', name: 'Bob Johnson', type: 'Refinance', date: '2026-06-24', status: 'Approved', risk: 'Low', score: 12 },
  { id: 'APP-2026-003', name: 'Charlie Davis', type: 'Purchase', date: '2026-06-24', status: 'Pending', risk: 'Medium', score: 45 },
  { id: 'APP-2026-004', name: 'Diana Prince', type: 'Purchase', date: '2026-06-23', status: 'Pending', risk: 'Low', score: 22 },
  { id: 'APP-2026-005', name: 'Evan Wright', type: 'Refinance', date: '2026-06-22', status: 'Rejected', risk: 'High', score: 92 },
];

export default function DashboardPage() {
  return (
    <div className="p-8 space-y-8">
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-slate-500">Total Applications</CardTitle>
            <FileText className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,248</div>
            <p className="text-xs text-slate-400 mt-1">+12% from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-slate-500">Pending Review</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">42</div>
            <p className="text-xs text-slate-400 mt-1">18 require urgent action</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-slate-500">High Risk Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">7</div>
            <p className="text-xs text-slate-400 mt-1">Fraud flags detected</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-slate-500">Approved Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">24</div>
            <p className="text-xs text-slate-400 mt-1">Avg processing time: 4h</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Applications</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>App ID</TableHead>
                <TableHead>Applicant</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Risk Score</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockApplications.map((app) => (
                <TableRow key={app.id}>
                  <TableCell className="font-medium">{app.id}</TableCell>
                  <TableCell>{app.name}</TableCell>
                  <TableCell>{app.type}</TableCell>
                  <TableCell>{app.date}</TableCell>
                  <TableCell>
                    <Badge variant={app.status === 'Approved' ? 'success' : app.status === 'Rejected' ? 'destructive' : 'secondary'}>
                      {app.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={
                      app.risk === 'High' ? 'border-red-500 text-red-700 bg-red-50' : 
                      app.risk === 'Medium' ? 'border-amber-500 text-amber-700 bg-amber-50' : 
                      'border-emerald-500 text-emerald-700 bg-emerald-50'
                    }>
                      {app.score} ({app.risk})
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Link href={`/application/${app.id}`}>
                      <Button variant="ghost" size="sm">
                        Review <ArrowRight className="ml-2 h-4 w-4" />
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
