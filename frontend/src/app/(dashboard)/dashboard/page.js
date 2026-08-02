'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, Clock, AlertTriangle, CheckCircle, ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { api } from '@/lib/api';
import { formatRiskScoreBadge, loanTypeLabel, riskDisplay } from "@/lib/risk-display";

export default function DashboardPage() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchApplications = async () => {
      try {
        const response = await api.getSubmissions({ limit: 5 });
        setApplications(response.data || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchApplications();
  }, []);

  const totalApps = applications.length;
  const pendingApps = applications.filter(app => app.submission_status === 'in_review').length;
  const highRiskApps = applications.filter(app => app.risk_level === 'high').length;
  const approvedApps = applications.filter(app => app.submission_status === 'approved').length;

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
            {loading ? <Loader2 className="h-6 w-6 animate-spin text-slate-300" /> : (
              <>
                <div className="text-2xl font-bold">{totalApps}</div>
                <p className="text-xs text-slate-400 mt-1">Based on recent data</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-slate-500">Pending Review</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            {loading ? <Loader2 className="h-6 w-6 animate-spin text-slate-300" /> : (
              <>
                <div className="text-2xl font-bold">{pendingApps}</div>
                <p className="text-xs text-slate-400 mt-1">Requires action</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-slate-500">High Risk Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            {loading ? <Loader2 className="h-6 w-6 animate-spin text-slate-300" /> : (
              <>
                <div className="text-2xl font-bold text-red-600">{highRiskApps}</div>
                <p className="text-xs text-slate-400 mt-1">Requires close attention</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-slate-500">Approved</CardTitle>
            <CheckCircle className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            {loading ? <Loader2 className="h-6 w-6 animate-spin text-slate-300" /> : (
              <>
                <div className="text-2xl font-bold">{approvedApps}</div>
                <p className="text-xs text-slate-400 mt-1">Ready for settlement</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Main Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Applications</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
             <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin text-blue-500" /></div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>App ID</TableHead>
                  <TableHead>Applicant</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {applications.map((app) => (
                  <TableRow key={app.id}>
                    <TableCell className="font-medium">{app.id}</TableCell>
                    <TableCell>{app.customer_name}</TableCell>
                    <TableCell>{loanTypeLabel(app.loan_type)}</TableCell>
                    <TableCell>{new Date(app.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={
                        app.submission_status === 'rejected' ? 'border-red-500 text-red-700 bg-red-50' : 
                        app.submission_status === 'approved' ? 'border-emerald-500 text-emerald-700 bg-emerald-50' : 
                        app.submission_status === 'in_review' ? 'border-amber-500 text-amber-700 bg-amber-50' : 
                        'bg-slate-100 text-slate-700'
                      }>
                        {app.submission_status.toUpperCase().replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {(() => {
                        const riskBadge = formatRiskScoreBadge(app);
                        const risk = riskDisplay(app.risk_level);
                        return (
                          <Badge variant="outline" className={riskBadge.className}>
                            {riskBadge.scoreText != null
                              ? `${riskBadge.scoreText} (${risk.label})`
                              : riskBadge.label}
                          </Badge>
                        );
                      })()}
                    </TableCell>
                    <TableCell>
                      <Link href={`/application/${app.id}`}>
                        <Button variant="ghost" size="sm" className="-ml-3">
                          Review <ArrowRight className="ml-2 h-4 w-4" />
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
                {applications.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-6 text-slate-500">
                      No applications found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
