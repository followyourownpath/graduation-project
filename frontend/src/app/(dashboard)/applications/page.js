import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowRight, Plus, Search, Filter } from "lucide-react";
import Link from "next/link";

const mockApplications = [
  { id: 'APP-2026-001', name: 'Alice Smith', type: 'Purchase', date: '2026-06-25', status: 'Pending', risk: 'High', score: 85 },
  { id: 'APP-2026-002', name: 'Bob Johnson', type: 'Refinance', date: '2026-06-24', status: 'Approved', risk: 'Low', score: 12 },
  { id: 'APP-2026-003', name: 'Charlie Davis', type: 'Purchase', date: '2026-06-24', status: 'Pending', risk: 'Medium', score: 45 },
  { id: 'APP-2026-004', name: 'Diana Prince', type: 'Purchase', date: '2026-06-23', status: 'Pending', risk: 'Low', score: 22 },
  { id: 'APP-2026-005', name: 'Evan Wright', type: 'Refinance', date: '2026-06-22', status: 'Rejected', risk: 'High', score: 92 },
  { id: 'APP-2026-006', name: 'Fiona Gallagher', type: 'Purchase', date: '2026-06-21', status: 'Approved', risk: 'Low', score: 18 },
  { id: 'APP-2026-007', name: 'George Miller', type: 'Refinance', date: '2026-06-20', status: 'Pending', risk: 'Medium', score: 55 },
];

export default function ApplicationsPage() {
  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Applications Management</h1>
          <p className="text-sm text-slate-500 mt-1">View and manage all mortgage applications in the system.</p>
        </div>
        <Link href="/applications/new">
          <Button className="bg-blue-600 hover:bg-blue-700">
            <Plus className="mr-2 h-4 w-4" />
            New Application
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader className="pb-3 border-b border-slate-100">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="relative w-full sm:w-96">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search by Applicant or ID..."
                className="pl-9"
              />
            </div>
            <Button variant="outline" className="w-full sm:w-auto">
              <Filter className="mr-2 h-4 w-4" />
              Filters
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
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
