# Frontend Integration Guide

This document provides comprehensive guidance for integrating the Investment Readiness Report backend with frontend applications.

## Overview

The backend provides a complete API for generating AI-powered investment readiness reports with structured JSON data optimized for frontend consumption.

## Report Generation Workflow

### 1. Analysis Request Submission

**Frontend Action**: User submits analysis form through `AnalysisSubmissionForm`

**API Call**:
```javascript
// Option 1: Direct API call
const response = await fetch('/api/reports', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token // if auth required
  },
  body: JSON.stringify({
    user_id: "uuid-string",
    title: "Founder Due Diligence Report for John Doe",
    founder_name: "John Doe",
    company_name: "Example Startup Inc",
    email: "founder@example.com",
    industry: "Technology",
    funding_stage: "Seed",
    company_type: "SaaS",
    additional_info: "Additional context...",
    pitch_deck_url: "https://supabase-url/pitch-deck.pdf"
  })
});

const analysisRequest = await response.json();

// Option 2: Via Supabase Edge Function (if using Supabase)
const { data, error } = await supabase.functions.invoke('generate-analysis-report', {
  body: { analysisRequestId: analysisRequest.id }
});
```

### 2. Report Generation Trigger

**API Call**:
```javascript
const generateResponse = await fetch(`/api/reports/${analysisRequest.id}/generate`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
});

const generationResult = await generateResponse.json();
// Returns: { message, external_request_id, deal_id }
```

### 3. Status Monitoring

**Polling Implementation**:
```javascript
const pollReportStatus = async (reportId, maxAttempts = 60, interval = 5000) => {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const response = await fetch(`/api/reports/${reportId}/status`);
    const status = await response.json();
    
    if (status.status === 'completed') {
      return { success: true, status };
    } else if (status.status === 'failed') {
      return { success: false, error: 'Report generation failed' };
    }
    
    // Update UI with progress
    updateProgressBar(status.progress);
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  
  return { success: false, error: 'Timeout waiting for report completion' };
};
```

### 4. Data Retrieval and Display

**Loading Report Data**:
```javascript
// Load from deal_report_summaries table
const { data: summary, error } = await supabase
  .from('deal_report_summaries')
  .select('*')
  .eq('deal_id', dealId)
  .maybeSingle();

if (error) {
  console.error('Error loading report summary:', error);
  return;
}

// Parse JSON sections for React components
const reportData = {
  executiveSummary: JSON.parse(summary.executive_summary),
  strategicRecommendations: JSON.parse(summary.strategic_recommendations),
  marketAnalysis: JSON.parse(summary.market_analysis),
  financialOverview: JSON.parse(summary.financial_overview),
  competitiveLandscape: JSON.parse(summary.competitive_landscape),
  actionPlan: JSON.parse(summary.action_plan),
  investmentReadiness: JSON.parse(summary.investment_readiness)
};
```

## React Component Integration

### Executive Summary Component

```jsx
import React from 'react';

const ExecutiveSummary = ({ data }) => {
  if (!data) return <div>Loading executive summary...</div>;

  return (
    <div className="executive-summary">
      <h2>Executive Summary</h2>
      
      <div className="overview">
        <h3>Overview</h3>
        <p>{data.context_purpose}</p>
        
        <div className="investment-attractiveness">
          <h4>Investment Attractiveness: {data.investment_attractiveness?.level}</h4>
          <p>{data.investment_attractiveness?.description}</p>
        </div>
      </div>

      <div className="key-metrics">
        <h3>Key Metrics</h3>
        <ul>
          {data.key_metrics?.map((metric, index) => (
            <li key={index}>{metric}</li>
          ))}
        </ul>
      </div>

      <div className="strengths-challenges">
        <div className="strengths">
          <h4>Strengths</h4>
          <ul>
            {data.strengths?.map((strength, index) => (
              <li key={index}>{strength}</li>
            ))}
          </ul>
        </div>
        
        <div className="challenges">
          <h4>Challenges</h4>
          <ul>
            {data.challenges?.map((challenge, index) => (
              <li key={index}>{challenge}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ExecutiveSummary;
```

### Action Plan Component

```jsx
import React from 'react';

const ActionPlan = ({ data }) => {
  if (!data) return <div>Loading action plan...</div>;

  const getColorClass = (color) => {
    const colorMap = {
      red: 'bg-red-100 text-red-800',
      yellow: 'bg-yellow-100 text-yellow-800',
      green: 'bg-green-100 text-green-800'
    };
    return colorMap[color] || 'bg-gray-100 text-gray-800';
  };

  const getIconComponent = (iconType) => {
    // Return appropriate icon component based on iconType
    // This would depend on your icon library (e.g., Heroicons, Lucide, etc.)
    return <span className="icon">{iconType}</span>;
  };

  return (
    <div className="action-plan">
      <h2>Action Plan</h2>
      
      <div className="timeframes">
        {data.timeframes?.map((timeframe, index) => (
          <div key={index} className={`timeframe ${getColorClass(timeframe.color)}`}>
            <div className="timeframe-header">
              {getIconComponent(timeframe.icon_type)}
              <h3>{timeframe.period}</h3>
            </div>
            
            <ul className="actions">
              {timeframe.actions?.map((action, actionIndex) => (
                <li key={actionIndex}>{action}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {data.final_call_to_action && (
        <div className="final-call-to-action">
          <h3>{data.final_call_to_action.title}</h3>
          {data.final_call_to_action.sections?.map((section, index) => (
            <div key={index} className="cta-section">
              <h4>{section.title}</h4>
              <p>{section.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActionPlan;
```

### Investment Readiness Component

```jsx
import React from 'react';

const InvestmentReadiness = ({ data }) => {
  if (!data) return <div>Loading investment readiness...</div>;

  const getStatusColor = (statusLevel) => {
    const colorMap = {
      high: 'text-green-600',
      moderate: 'text-yellow-600',
      low: 'text-red-600'
    };
    return colorMap[statusLevel] || 'text-gray-600';
  };

  return (
    <div className="investment-readiness">
      <h2>{data.title}</h2>
      
      <div className="categories">
        {data.categories?.map((category, index) => (
          <div key={index} className="category-item">
            <div className="category-header">
              <h3>{category.category}</h3>
              <span className={`status ${getStatusColor(category.statusLevel)}`}>
                {category.status}
              </span>
            </div>
            <p className="evidence">{category.evidence}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default InvestmentReadiness;
```

## Error Handling

### API Error Handling

```javascript
const handleApiError = (error, context) => {
  console.error(`Error in ${context}:`, error);
  
  if (error.status === 401) {
    // Handle authentication error
    redirectToLogin();
  } else if (error.status === 429) {
    // Handle rate limiting
    showRateLimitMessage();
  } else if (error.status >= 500) {
    // Handle server errors
    showServerErrorMessage();
  } else {
    // Handle other errors
    showGenericErrorMessage(error.message);
  }
};
```

### Data Validation

```javascript
const validateReportData = (data) => {
  const requiredFields = [
    'executive_summary',
    'strategic_recommendations',
    'market_analysis',
    'financial_overview',
    'competitive_landscape',
    'action_plan',
    'investment_readiness'
  ];

  for (const field of requiredFields) {
    if (!data[field]) {
      console.warn(`Missing required field: ${field}`);
      return false;
    }
    
    try {
      JSON.parse(data[field]);
    } catch (e) {
      console.error(`Invalid JSON in field ${field}:`, e);
      return false;
    }
  }
  
  return true;
};
```

## Performance Optimization

### Lazy Loading Components

```jsx
import React, { lazy, Suspense } from 'react';

const ExecutiveSummary = lazy(() => import('./ExecutiveSummary'));
const ActionPlan = lazy(() => import('./ActionPlan'));
const InvestmentReadiness = lazy(() => import('./InvestmentReadiness'));

const ReportView = ({ reportData }) => {
  return (
    <div className="report-view">
      <Suspense fallback={<div>Loading executive summary...</div>}>
        <ExecutiveSummary data={reportData.executiveSummary} />
      </Suspense>
      
      <Suspense fallback={<div>Loading action plan...</div>}>
        <ActionPlan data={reportData.actionPlan} />
      </Suspense>
      
      <Suspense fallback={<div>Loading investment readiness...</div>}>
        <InvestmentReadiness data={reportData.investmentReadiness} />
      </Suspense>
    </div>
  );
};
```

### Caching Strategy

```javascript
// Use React Query or SWR for caching
import { useQuery } from 'react-query';

const useReportData = (dealId) => {
  return useQuery(
    ['report', dealId],
    async () => {
      const { data, error } = await supabase
        .from('deal_report_summaries')
        .select('*')
        .eq('deal_id', dealId)
        .maybeSingle();
      
      if (error) throw error;
      return data;
    },
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    }
  );
};
```

## Testing

### Unit Tests for Components

```javascript
import { render, screen } from '@testing-library/react';
import ExecutiveSummary from './ExecutiveSummary';

const mockData = {
  context_purpose: "Test executive summary",
  investment_attractiveness: {
    level: "high",
    description: "Strong investment potential"
  },
  key_metrics: ["Revenue: $1M", "Growth: 50%"],
  strengths: ["Strong team"],
  challenges: ["Competition"]
};

test('renders executive summary correctly', () => {
  render(<ExecutiveSummary data={mockData} />);
  
  expect(screen.getByText('Executive Summary')).toBeInTheDocument();
  expect(screen.getByText('Test executive summary')).toBeInTheDocument();
  expect(screen.getByText('Investment Attractiveness: high')).toBeInTheDocument();
});
```

### Integration Tests

```javascript
import { render, waitFor } from '@testing-library/react';
import ReportView from './ReportView';

// Mock Supabase
jest.mock('@supabase/supabase-js');

test('loads and displays report data', async () => {
  const mockSupabase = {
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        eq: jest.fn(() => ({
          maybeSingle: jest.fn(() => Promise.resolve({
            data: mockReportData,
            error: null
          }))
        }))
      }))
    }))
  };

  render(<ReportView dealId="test-deal-123" supabase={mockSupabase} />);
  
  await waitFor(() => {
    expect(screen.getByText('Executive Summary')).toBeInTheDocument();
  });
});
```

This integration guide provides everything needed to successfully integrate the backend API with frontend applications, including React components, error handling, performance optimization, and testing strategies.
