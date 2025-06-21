# Detailed Frontend Workflow for Investment Readiness Reports

## Complete Frontend Integration Guide

This document provides the exact step-by-step frontend workflow for implementing the Investment Readiness Report system, including all API calls, database queries, UI components, and state management.

## 🔄 Complete Report Generation Workflow

### Phase 1: Initial Request Submission

#### 1.1 Frontend Form Component (AnalysisSubmissionForm)
```typescript
// components/AnalysisSubmissionForm.tsx
import { useState } from 'react';
import { supabase } from '@/lib/supabase';

interface AnalysisFormData {
  founder_name: string;
  company_name?: string;
  requestor_name?: string;
  email?: string;
  industry?: string;
  funding_stage?: string;
  company_type?: string;
  additional_info?: string;
  pitch_deck_url?: string;
}

export function AnalysisSubmissionForm() {
  const [formData, setFormData] = useState<AnalysisFormData>({
    founder_name: '',
    company_name: 'Right Hand Operation',
    requestor_name: '',
    email: '',
    industry: '',
    funding_stage: '',
    company_type: '',
    additional_info: '',
    pitch_deck_url: ''
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Step 1: Create analysis request via backend API
      const response = await fetch('/api/reports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: (await supabase.auth.getUser()).data.user?.id,
          ...formData
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create analysis request');
      }

      const analysisRequest = await response.json();
      setRequestId(analysisRequest.id);

      // Step 2: Immediately trigger report generation
      await triggerReportGeneration(analysisRequest.id);
      
    } catch (error) {
      console.error('Error submitting analysis request:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const triggerReportGeneration = async (requestId: string) => {
    try {
      const response = await fetch(`/api/reports/${requestId}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error('Failed to trigger report generation');
      }

      // Redirect to status monitoring page
      window.location.href = `/report-status/${requestId}`;
      
    } catch (error) {
      console.error('Error triggering report generation:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Form fields */}
      <div>
        <label htmlFor="founder_name" className="block text-sm font-medium">
          Founder Name *
        </label>
        <input
          type="text"
          id="founder_name"
          required
          value={formData.founder_name}
          onChange={(e) => setFormData({...formData, founder_name: e.target.value})}
          className="mt-1 block w-full rounded-md border-gray-300"
        />
      </div>

      <div>
        <label htmlFor="requestor_name" className="block text-sm font-medium">
          Your Name
        </label>
        <input
          type="text"
          id="requestor_name"
          value={formData.requestor_name}
          onChange={(e) => setFormData({...formData, requestor_name: e.target.value})}
          className="mt-1 block w-full rounded-md border-gray-300"
        />
      </div>

      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email Address
        </label>
        <input
          type="email"
          id="email"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          className="mt-1 block w-full rounded-md border-gray-300"
        />
      </div>

      <div>
        <label htmlFor="industry" className="block text-sm font-medium">
          Industry
        </label>
        <select
          id="industry"
          value={formData.industry}
          onChange={(e) => setFormData({...formData, industry: e.target.value})}
          className="mt-1 block w-full rounded-md border-gray-300"
        >
          <option value="">Select Industry</option>
          <option value="Technology">Technology</option>
          <option value="Healthcare">Healthcare</option>
          <option value="Finance">Finance</option>
          <option value="E-commerce">E-commerce</option>
          <option value="SaaS">SaaS</option>
          <option value="Other">Other</option>
        </select>
      </div>

      <div>
        <label htmlFor="funding_stage" className="block text-sm font-medium">
          Funding Stage
        </label>
        <select
          id="funding_stage"
          value={formData.funding_stage}
          onChange={(e) => setFormData({...formData, funding_stage: e.target.value})}
          className="mt-1 block w-full rounded-md border-gray-300"
        >
          <option value="">Select Stage</option>
          <option value="Pre-Seed">Pre-Seed</option>
          <option value="Seed">Seed</option>
          <option value="Series A">Series A</option>
          <option value="Series B">Series B</option>
          <option value="Series C+">Series C+</option>
        </select>
      </div>

      <div>
        <label htmlFor="pitch_deck_url" className="block text-sm font-medium">
          Pitch Deck URL
        </label>
        <input
          type="url"
          id="pitch_deck_url"
          value={formData.pitch_deck_url}
          onChange={(e) => setFormData({...formData, pitch_deck_url: e.target.value})}
          className="mt-1 block w-full rounded-md border-gray-300"
          placeholder="https://example.com/pitch-deck.pdf"
        />
      </div>

      <div>
        <label htmlFor="additional_info" className="block text-sm font-medium">
          Additional Information
        </label>
        <textarea
          id="additional_info"
          rows={4}
          value={formData.additional_info}
          onChange={(e) => setFormData({...formData, additional_info: e.target.value})}
          className="mt-1 block w-full rounded-md border-gray-300"
          placeholder="Founder Company: [Company Name]&#10;Any additional context about the founder or company..."
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Submitting...' : 'Generate Investment Readiness Report'}
      </button>
    </form>
  );
}
```

### Phase 2: Real-Time Status Monitoring

#### 2.1 Report Status Component
```typescript
// components/ReportStatusMonitor.tsx
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

interface ReportStatus {
  report_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
}

export function ReportStatusMonitor({ requestId }: { requestId: string }) {
  const [status, setStatus] = useState<ReportStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/reports/${requestId}/status`);
        if (!response.ok) {
          throw new Error('Failed to fetch status');
        }
        
        const statusData = await response.json();
        setStatus(statusData);

        // If completed, redirect to report view
        if (statusData.status === 'completed') {
          setTimeout(() => {
            router.push(`/report/${requestId}`);
          }, 2000);
        }
        
        // If failed, show error
        if (statusData.status === 'failed') {
          setError('Report generation failed. Please try again.');
        }
        
      } catch (err) {
        setError('Failed to check report status');
      }
    };

    // Poll every 5 seconds
    const interval = setInterval(pollStatus, 5000);
    
    // Initial poll
    pollStatus();

    return () => clearInterval(interval);
  }, [requestId, router]);

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 text-lg font-medium">{error}</div>
        <button 
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!status) {
    return <div className="text-center py-12">Loading...</div>;
  }

  return (
    <div className="text-center py-12">
      <div className="max-w-md mx-auto">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Generating Your Investment Readiness Report
        </h2>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2.5 mb-6">
          <div 
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
            style={{ width: `${status.progress}%` }}
          ></div>
        </div>

        {/* Status Messages */}
        <div className="space-y-4">
          {status.status === 'pending' && (
            <p className="text-gray-600">Preparing your analysis request...</p>
          )}
          {status.status === 'processing' && (
            <div className="space-y-2">
              <p className="text-blue-600 font-medium">Analyzing founder and company data...</p>
              <p className="text-sm text-gray-500">
                Our AI is generating comprehensive insights across 7 key areas
              </p>
            </div>
          )}
          {status.status === 'completed' && (
            <div className="space-y-2">
              <p className="text-green-600 font-medium">✅ Report completed successfully!</p>
              <p className="text-sm text-gray-500">Redirecting to your report...</p>
            </div>
          )}
        </div>

        <div className="mt-8 text-sm text-gray-500">
          <p>Report ID: {requestId}</p>
          <p>This process typically takes 2-3 minutes</p>
        </div>
      </div>
    </div>
  );
}
```

### Phase 3: Report Content Display

#### 3.1 Full Report View Component
```typescript
// components/ReportView.tsx
import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

interface ReportSection {
  id: string;
  title: string;
  content: string;
  sub_sections: ReportSection[];
}

interface ReportContent {
  status: string;
  url: string | null;
  sections: ReportSection[];
}

export function ReportView({ requestId }: { requestId: string }) {
  const [reportContent, setReportContent] = useState<ReportContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReportContent = async () => {
      try {
        const response = await fetch(`/api/reports/${requestId}/content`);
        if (!response.ok) {
          throw new Error('Failed to fetch report content');
        }
        
        const content = await response.json();
        setReportContent(content);
        
      } catch (err) {
        setError('Failed to load report content');
      } finally {
        setLoading(false);
      }
    };

    fetchReportContent();
  }, [requestId]);

  if (loading) {
    return <div className="text-center py-12">Loading report...</div>;
  }

  if (error) {
    return <div className="text-center py-12 text-red-600">{error}</div>;
  }

  if (!reportContent) {
    return <div className="text-center py-12">No report content available</div>;
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Report Header */}
      <div className="mb-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Investment Readiness Report
            </h1>
            <p className="text-gray-600">Generated on {new Date().toLocaleDateString()}</p>
          </div>
          
          {/* PDF Download Button */}
          {reportContent.url && (
            <a
              href={reportContent.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              📄 Download PDF
            </a>
          )}
        </div>
      </div>

      {/* Report Sections */}
      <div className="space-y-8">
        {reportContent.sections.map((section, index) => (
          <div key={section.id} className="bg-white rounded-lg shadow-sm border p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              {section.title}
            </h2>
            <div 
              className="prose max-w-none text-gray-700"
              dangerouslySetInnerHTML={{ __html: section.content }}
            />
            
            {/* Sub-sections */}
            {section.sub_sections.length > 0 && (
              <div className="mt-6 space-y-4">
                {section.sub_sections.map((subSection) => (
                  <div key={subSection.id} className="border-l-4 border-blue-200 pl-4">
                    <h3 className="font-medium text-gray-900 mb-2">
                      {subSection.title}
                    </h3>
                    <div 
                      className="text-gray-700"
                      dangerouslySetInnerHTML={{ __html: subSection.content }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Report Footer */}
      <div className="mt-12 pt-8 border-t border-gray-200">
        <div className="text-center text-sm text-gray-500">
          <p>This report was generated using AI-powered analysis</p>
          <p>Report ID: {requestId}</p>
        </div>
      </div>
    </div>
  );
}
```

### Phase 4: Dashboard Integration

#### 4.1 Deal Dashboard with Supabase Integration
```typescript
// components/DealDashboard.tsx
import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

interface DealSummary {
  deal_id: string;
  company_name: string;
  executive_summary: string;
  strategic_recommendations: string;
  market_analysis: string;
  financial_overview: string;
  competitive_landscape: string;
  action_plan: string;
  investment_readiness: string;
  key_metrics: any;
  financial_projections: any;
}

interface DealReport {
  deal_id: string;
  company_name: string;
  pdf_url: string | null;
  pdf_file_path: string | null;
}

export function DealDashboard() {
  const [deals, setDeals] = useState<DealSummary[]>([]);
  const [reports, setReports] = useState<DealReport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDeals = async () => {
      try {
        // Fetch deal summaries
        const { data: summaries, error: summariesError } = await supabase
          .from('deal_report_summaries')
          .select('*')
          .order('created_at', { ascending: false });

        if (summariesError) throw summariesError;

        // Fetch deal reports (for PDF URLs)
        const { data: reportsData, error: reportsError } = await supabase
          .from('deal_reports')
          .select('*')
          .order('created_at', { ascending: false });

        if (reportsError) throw reportsError;

        setDeals(summaries || []);
        setReports(reportsData || []);
        
      } catch (error) {
        console.error('Error fetching deals:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDeals();
  }, []);

  if (loading) {
    return <div className="text-center py-12">Loading deals...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Deal Dashboard</h1>
        <p className="text-gray-600 mt-2">
          View and manage your investment readiness reports
        </p>
      </div>

      {/* Deal Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {deals.map((deal) => {
          const report = reports.find(r => r.deal_id === deal.deal_id);
          const executiveSummary = deal.executive_summary ? 
            JSON.parse(deal.executive_summary) : {};
          
          return (
            <div key={deal.deal_id} className="bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {deal.company_name}
                  </h3>
                  {report?.pdf_url && (
                    <a
                      href={report.pdf_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800"
                    >
                      📄
                    </a>
                  )}
                </div>

                {/* Executive Summary Preview */}
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Executive Summary
                  </h4>
                  <p className="text-sm text-gray-600 line-clamp-3">
                    {executiveSummary.overview || 'Analysis in progress...'}
                  </p>
                </div>

                {/* Key Metrics */}
                {deal.key_metrics && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      Status
                    </h4>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      {deal.key_metrics.api_status || 'Completed'}
                    </span>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex space-x-2">
                  <button
                    onClick={() => window.location.href = `/report-summary/${deal.deal_id}`}
                    className="flex-1 px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
                  >
                    View Summary
                  </button>
                  {report?.pdf_url && (
                    <button
                      onClick={() => window.open(report.pdf_url!, '_blank')}
                      className="px-3 py-2 text-sm font-medium text-gray-600 bg-gray-50 rounded-md hover:bg-gray-100"
                    >
                      PDF
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {deals.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No deals found. Create your first analysis request!</p>
          <button
            onClick={() => window.location.href = '/create-analysis'}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Create Analysis Request
          </button>
        </div>
      )}
    </div>
  );
}
```

#### 4.2 Structured Report Summary View
```typescript
// components/DealReportSummaryView.tsx
import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

interface StructuredSummary {
  deal_id: string;
  company_name: string;
  executive_summary: any;
  strategic_recommendations: any;
  market_analysis: any;
  financial_overview: any;
  competitive_landscape: any;
  action_plan: any;
  investment_readiness: any;
}

export function DealReportSummaryView({ dealId }: { dealId: string }) {
  const [summary, setSummary] = useState<StructuredSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const { data, error } = await supabase
          .from('deal_report_summaries')
          .select('*')
          .eq('deal_id', dealId)
          .maybeSingle();

        if (error) throw error;
        setSummary(data);
        
      } catch (error) {
        console.error('Error fetching summary:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [dealId]);

  if (loading) {
    return <div className="text-center py-12">Loading summary...</div>;
  }

  if (!summary) {
    return <div className="text-center py-12">Summary not found</div>;
  }

  const parseSection = (sectionData: string) => {
    try {
      return JSON.parse(sectionData);
    } catch {
      return {};
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          {summary.company_name} - Investment Analysis
        </h1>
      </div>

      <div className="space-y-8">
        {/* Executive Summary */}
        <SummarySection
          title="Executive Summary"
          data={parseSection(summary.executive_summary)}
        />

        {/* Market Analysis */}
        <SummarySection
          title="Market Analysis"
          data={parseSection(summary.market_analysis)}
        />

        {/* Financial Overview */}
        <SummarySection
          title="Financial Overview"
          data={parseSection(summary.financial_overview)}
        />

        {/* Competitive Landscape */}
        <SummarySection
          title="Competitive Landscape"
          data={parseSection(summary.competitive_landscape)}
        />

        {/* Investment Readiness */}
        <SummarySection
          title="Investment Readiness"
          data={parseSection(summary.investment_readiness)}
        />

        {/* Strategic Recommendations */}
        <SummarySection
          title="Strategic Recommendations"
          data={parseSection(summary.strategic_recommendations)}
        />

        {/* Action Plan */}
        <SummarySection
          title="Action Plan"
          data={parseSection(summary.action_plan)}
        />
      </div>
    </div>
  );
}

function SummarySection({ title, data }: { title: string; data: any }) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">{title}</h2>
        <p className="text-gray-500">Analysis in progress...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">{title}</h2>
      
      <div className="space-y-4">
        {Object.entries(data).map(([key, value]) => (
          <div key={key}>
            <h3 className="font-medium text-gray-900 capitalize mb-2">
              {key.replace(/_/g, ' ')}
            </h3>
            <div className="text-gray-700">
              {Array.isArray(value) ? (
                <ul className="list-disc list-inside space-y-1">
                  {value.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              ) : typeof value === 'object' ? (
                <div className="space-y-2">
                  {Object.entries(value).map(([subKey, subValue]) => (
                    <div key={subKey}>
                      <span className="font-medium">{subKey}:</span> {String(subValue)}
                    </div>
                  ))}
                </div>
              ) : (
                <p>{String(value)}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## 🔌 API Integration Summary

### Backend API Endpoints
```typescript
// API endpoints available for frontend integration

// 1. Create Analysis Request
POST /api/reports
Body: {
  user_id: string,
  founder_name: string,
  company_name?: string,
  requestor_name?: string,
  email?: string,
  industry?: string,
  funding_stage?: string,
  company_type?: string,
  additional_info?: string,
  pitch_deck_url?: string
}
Response: AnalysisRequestOut

// 2. Trigger Report Generation
POST /api/reports/{request_id}/generate
Response: AnalysisRequestOut

// 3. Check Report Status
GET /api/reports/{request_id}/status
Response: {
  report_id: string,
  status: 'pending' | 'processing' | 'completed' | 'failed',
  progress: number
}

// 4. Get Report Content
GET /api/reports/{request_id}/content
Response: {
  status: string,
  url: string | null,
  sections: ReportSection[]
}

// 5. Get Full Report Data
GET /api/reports/{request_id}
Response: AnalysisRequestOut

// 6. Webhook Handler (for external API callbacks)
POST /api/webhook/report-completion
Body: {
  reportId: string,
  pdfUrl: string,
  summaryData: object
}
```

### Supabase Database Queries
```typescript
// Database tables and queries for frontend

// 1. Analysis Requests (tracking user submissions)
const { data: requests } = await supabase
  .from('analysis_requests')
  .select('*')
  .eq('user_id', userId)
  .order('created_at', { ascending: false });

// 2. Deal Reports (PDF metadata)
const { data: reports } = await supabase
  .from('deal_reports')
  .select('*')
  .order('created_at', { ascending: false });

// 3. Deal Report Summaries (structured JSON content)
const { data: summaries } = await supabase
  .from('deal_report_summaries')
  .select('*')
  .eq('deal_id', dealId)
  .maybeSingle();

// 4. Real-time subscriptions for status updates
const subscription = supabase
  .channel('analysis_requests')
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'analysis_requests',
    filter: `id=eq.${requestId}`
  }, (payload) => {
    setStatus(payload.new.status);
  })
  .subscribe();
```

## 🎯 Complete User Journey

### Step-by-Step User Experience

1. **Form Submission** → User fills out AnalysisSubmissionForm
2. **Request Creation** → POST /api/reports creates analysis_requests record
3. **Generation Trigger** → POST /api/reports/{id}/generate starts AI processing
4. **Status Monitoring** → ReportStatusMonitor polls GET /api/reports/{id}/status
5. **Real-time Updates** → Supabase subscriptions provide live status updates
6. **Report Completion** → AI generates structured JSON + PDF
7. **Data Storage** → Results saved to deal_reports + deal_report_summaries
8. **Report Display** → ReportView shows full content with PDF download
9. **Dashboard Integration** → DealDashboard lists all completed reports
10. **Summary Views** → DealReportSummaryView shows structured analysis

### State Management Flow
```typescript
// Complete state flow for report generation
interface ReportState {
  // Form submission
  formData: AnalysisFormData;
  isSubmitting: boolean;
  
  // Request tracking
  requestId: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  
  // Content display
  reportContent: ReportContent | null;
  summaryData: StructuredSummary | null;
  
  // Error handling
  error: string | null;
  loading: boolean;
}
```

This comprehensive workflow provides complete frontend integration for the Investment Readiness Report system, with real-time status updates, structured data display, and seamless user experience from form submission to report viewing.
