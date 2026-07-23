'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowRight, Plus, Search, Filter, Loader2 } from "lucide-react";
import Link from "next/link";
import { api } from '@/lib/api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function ApplicationsPage() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [loanTypeFilter, setLoanTypeFilter] = useState('all');
  const [dateSortOrder, setDateSortOrder] = useState('desc');

  useEffect(() => {
    const fetchApplications = async () => {
      try {
        const response = await api.getSubmissions();
        setApplications(response.data || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchApplications();
  }, []);

  const filteredApplications = applications.filter(app => {
    const matchesSearch = 
      app.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
      (app.customer_name && app.customer_name.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesStatus = statusFilter === 'all' || app.submission_status === statusFilter;
    const matchesLoanType = loanTypeFilter === 'all' || app.loan_type === loanTypeFilter;

    return matchesSearch && matchesStatus && matchesLoanType;
  }).sort((a, b) => {
    const dateA = new Date(a.created_at).getTime();
    const dateB = new Date(b.created_at).getTime();
    return dateSortOrder === 'asc' ? dateA - dateB : dateB - dateA;
  });

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
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
              <Select value={loanTypeFilter} onValueChange={setLoanTypeFilter}>
                <SelectTrigger className="w-full sm:w-[240px]">
                  <Filter className="mr-2 h-4 w-4 text-slate-500" />
                  <SelectValue placeholder="Loan Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Loan Type</SelectItem>
                  <SelectItem value="purchase">Owner-Occupier Purchase</SelectItem>
                  <SelectItem value="investment">Investment Purchase</SelectItem>
                  <SelectItem value="refinance">Refinance</SelectItem>
                  <SelectItem value="first_home">First Home Buyer</SelectItem>
                  <SelectItem value="self_employed">Self-Employed (any)</SelectItem>
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-[150px]">
                  <Filter className="mr-2 h-4 w-4 text-slate-500" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Statuses</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="in_review">In Review</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
              <Select value={dateSortOrder} onValueChange={setDateSortOrder}>
                <SelectTrigger className="w-full sm:w-[220px]">
                  <Filter className="mr-2 h-4 w-4 text-slate-500" />
                  <SelectValue placeholder="Sort Date" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="desc">Sort by Date: Descending</SelectItem>
                  <SelectItem value="asc">Sort by Date: Ascending</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {loading ? (
            <div className="flex justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
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
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredApplications.map((app) => (
                  <TableRow key={app.id}>
                    <TableCell className="font-medium">{app.id}</TableCell>
                    <TableCell>{app.customer_name}</TableCell>
                    <TableCell>{
                      {
                        'purchase': 'Owner-Occupier Purchase',
                        'investment': 'Investment Purchase',
                        'refinance': 'Refinance',
                        'first_home': 'First Home Buyer',
                        'self_employed': 'Self-Employed (any)'
                      }[app.loan_type] || app.loan_type
                    }</TableCell>
                    <TableCell>{new Date(app.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Badge variant={app.submission_status === 'approved' ? 'success' : app.submission_status === 'rejected' ? 'destructive' : 'secondary'}>
                        {app.submission_status.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={
                        app.risk_level === 'High' ? 'border-red-500 text-red-700 bg-red-50' : 
                        app.risk_level === 'Medium' ? 'border-amber-500 text-amber-700 bg-amber-50' : 
                        'border-emerald-500 text-emerald-700 bg-emerald-50'
                      }>
                        {app.overall_risk_score} {app.risk_level && `(${app.risk_level})`}
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
                {filteredApplications.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-6 text-slate-500">
                      No applications found matching your criteria.
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
