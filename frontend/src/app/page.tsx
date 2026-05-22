"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, CheckCircle2, ChevronRight, Loader2, Sparkles, TrendingUp, Search, Zap, Shield, Mail, Download } from "lucide-react";

type PipelineStep = "submitted" | "validating" | "enriching" | "generating_pdf" | "sending_email" | "logging" | "complete" | "error";

export default function Home() {
  const [appState, setAppState] = useState<"idle" | "processing" | "success" | "error">("idle");
  const [currentBackendStep, setCurrentBackendStep] = useState<PipelineStep>("submitted");
  const [completedSteps, setCompletedSteps] = useState<PipelineStep[]>([]);
  const [leadId, setLeadId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    website: "",
    industry: "",
    message: "",
    company_size: "Unknown"
  });

  const stepMapping: Record<PipelineStep, { label: string; order: number }> = {
    submitted: { label: "Initializing audit engine...", order: 0 },
    validating: { label: "Validating company metrics...", order: 1 },
    enriching: { label: "Scraping site & generating AI analysis...", order: 2 },
    generating_pdf: { label: "Designing personalized PDF report...", order: 3 },
    sending_email: { label: "Dispatching secure email...", order: 4 },
    logging: { label: "Finalizing audit logs...", order: 5 },
    complete: { label: "Done", order: 6 },
    error: { label: "Error encountered", order: 7 }
  };

  const orderedSteps = [
    "submitted", "validating", "enriching", "generating_pdf", "sending_email", "logging"
  ] as PipelineStep[];

  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const startPolling = (id: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    
    pollingRef.current = setInterval(async () => {
      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${API_BASE}/api/leads/${id}/status`);
        if (res.ok) {
          const data = await res.json();
          setCurrentBackendStep(data.current_step);
          setCompletedSteps(data.steps_completed || []);
          
          if (data.is_complete) {
            if (pollingRef.current) clearInterval(pollingRef.current);
            if (data.current_step === "error") {
              setErrorMessage(data.error_message || "An unknown error occurred during AI analysis.");
              setAppState("error");
            } else {
              setAppState("success");
            }
          }
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);
  };

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Auto-format website URL
    let formattedWebsite = formData.website.trim();
    if (formattedWebsite && !/^https?:\/\//i.test(formattedWebsite)) {
      formattedWebsite = `https://${formattedWebsite}`;
    }
    const finalFormData = { ...formData, website: formattedWebsite };

    setAppState("processing");
    setCurrentBackendStep("submitted");
    setCompletedSteps([]);
    setErrorMessage(null);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_BASE}/api/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(finalFormData),
      });
      
      if (res.ok) {
        const data = await res.json();
        setLeadId(data.lead_id);
        startPolling(data.lead_id);
      } else {
        setAppState("error");
        setErrorMessage("Failed to submit the audit request to the server.");
      }
    } catch (err) {
      setAppState("error");
      setErrorMessage("Could not connect to the backend API.");
    }
  };

  const handleDownload = () => {
    if (leadId) {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      window.open(`${API_BASE}/api/leads/${leadId}/pdf`, "_blank");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-indigo-100">
      
      {/* Navigation */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 font-semibold text-lg tracking-tight cursor-pointer" onClick={() => setAppState("idle")}>
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          Lead Autopilot
        </div>
        <div className="hidden md:flex gap-6 text-sm font-medium text-slate-500">
          <a href="#" className="hover:text-slate-900 transition-colors">How it Works</a>
          <a href="#" className="hover:text-slate-900 transition-colors">Examples</a>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-8 pb-24">
        
        <AnimatePresence mode="wait">
          {appState === "idle" && (
            <motion.div 
              key="landing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="grid lg:grid-cols-2 gap-16 mt-16 items-start"
            >
              
              {/* Left Column: Copy & Insights */}
              <div className="space-y-12">
                <div className="space-y-6">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold uppercase tracking-wider">
                    <Zap className="w-3.5 h-3.5" /> AI-Powered Analysis
                  </div>
                  <h1 className="text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 leading-[1.1]">
                    Get an intelligent business audit in minutes.
                  </h1>
                  <p className="text-xl text-slate-500 leading-relaxed max-w-lg">
                    We autonomously scrape your company website, leverage AI to identify growth opportunities, and deliver a personalized 5-page PDF report.
                  </p>
                </div>

                {/* Fake Insights Preview */}
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-1 h-full bg-indigo-600"></div>
                  <div className="flex items-center gap-3 mb-4">
                    <Search className="w-5 h-5 text-indigo-600" />
                    <h3 className="font-semibold text-slate-900">Live Analysis Engine</h3>
                  </div>
                  <ul className="space-y-3 text-sm text-slate-600">
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5" />
                      <span><strong>Web Scraping:</strong> Extracts services, tech stack, and brand tone.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5" />
                      <span><strong>AI Intelligence:</strong> Generates SWOT analysis and conversion insights.</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5" />
                      <span><strong>Dynamic Reporting:</strong> Themed PDF built and emailed instantly.</span>
                    </li>
                  </ul>
                  <div className="mt-5 text-xs text-slate-400 font-medium uppercase tracking-wider">Production Architecture</div>
                </div>

                {/* How it works */}
                <div className="pt-8 border-t border-slate-200">
                  <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-6">How it works</h3>
                  <div className="grid sm:grid-cols-3 gap-6">
                    <div>
                      <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold mb-3">1</div>
                      <p className="text-sm text-slate-600 font-medium">Submit your company details.</p>
                    </div>
                    <div>
                      <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold mb-3">2</div>
                      <p className="text-sm text-slate-600 font-medium">Celery queue processes data autonomously.</p>
                    </div>
                    <div>
                      <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold mb-3">3</div>
                      <p className="text-sm text-slate-600 font-medium">Download your PDF or check your inbox.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Premium Form */}
              <div className="bg-white rounded-[2rem] p-8 lg:p-12 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] border border-slate-100 relative">
                <div className="absolute -top-10 -right-10 w-40 h-40 bg-indigo-500/10 rounded-full blur-3xl"></div>
                <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl"></div>
                
                <h2 className="text-2xl font-bold text-slate-900 mb-2">Request Free Audit</h2>
                <p className="text-slate-500 mb-8 text-sm">Enter your details to generate your strategic report.</p>
                
                <form onSubmit={handleSubmit} className="space-y-5 relative z-10">
                  <div className="grid grid-cols-2 gap-5">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Full Name</label>
                      <input 
                        required
                        type="text" 
                        value={formData.name}
                        onChange={(e) => setFormData({...formData, name: e.target.value})}
                        className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none text-slate-900"
                        placeholder="Jane Doe"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Work Email</label>
                      <input 
                        required
                        type="email" 
                        value={formData.email}
                        onChange={(e) => setFormData({...formData, email: e.target.value})}
                        className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none text-slate-900"
                        placeholder="jane@company.com"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-5">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Company Name</label>
                      <input 
                        required
                        type="text" 
                        value={formData.company}
                        onChange={(e) => setFormData({...formData, company: e.target.value})}
                        className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none text-slate-900"
                        placeholder="Acme Corp"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-slate-700">Website URL</label>
                      <input 
                        required
                        type="text" 
                        value={formData.website}
                        onChange={(e) => setFormData({...formData, website: e.target.value})}
                        className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none text-slate-900"
                        placeholder="acme.com"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700">Industry <span className="text-slate-400 font-normal">(Optional)</span></label>
                    <input 
                      type="text" 
                      value={formData.industry}
                      onChange={(e) => setFormData({...formData, industry: e.target.value})}
                      className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none text-slate-900"
                      placeholder="e.g. SaaS, Healthcare, Finance"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700">What are you trying to improve? <span className="text-slate-400 font-normal">(Optional)</span></label>
                    <textarea 
                      rows={3}
                      value={formData.message}
                      onChange={(e) => setFormData({...formData, message: e.target.value})}
                      className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all outline-none text-slate-900 resize-none"
                      placeholder="Tell us about your current challenges so the AI can provide better context..."
                    ></textarea>
                  </div>

                  <button 
                    type="submit"
                    className="w-full mt-2 bg-slate-900 hover:bg-slate-800 text-white font-medium py-3.5 px-6 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-slate-900/20 group"
                  >
                    Generate Report
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </button>
                  <p className="text-center text-xs text-slate-400 mt-4 flex items-center justify-center gap-1.5">
                    <Shield className="w-3.5 h-3.5" /> Your data is securely processed in the background queue.
                  </p>
                </form>
              </div>

            </motion.div>
          )}

          {appState === "processing" && (
            <motion.div 
              key="processing"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="max-w-xl mx-auto mt-24 bg-white rounded-[2rem] p-12 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] border border-slate-100 text-center relative overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-1 bg-slate-100">
                <motion.div 
                  className="h-full bg-indigo-600"
                  initial={{ width: "0%" }}
                  animate={{ width: `${(stepMapping[currentBackendStep]?.order / (orderedSteps.length)) * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
              
              <div className="w-20 h-20 bg-indigo-50 rounded-2xl mx-auto flex items-center justify-center mb-8 relative">
                <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
              </div>

              <h2 className="text-2xl font-bold text-slate-900 mb-3">AI Engine Processing</h2>
              <p className="text-slate-500 mb-8">Live progress from our backend Celery workers.</p>

              <div className="space-y-4 text-left bg-slate-50 p-6 rounded-2xl border border-slate-100">
                {orderedSteps.map((stepKey) => {
                  const isCompleted = completedSteps.includes(stepKey);
                  const isActive = currentBackendStep === stepKey;
                  
                  return (
                    <motion.div 
                      key={stepKey}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: isCompleted || isActive ? 1 : 0.3, x: 0 }}
                      className="flex items-center gap-3"
                    >
                      {isCompleted ? (
                         <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                      ) : isActive ? (
                        <Loader2 className="w-5 h-5 text-indigo-600 animate-spin shrink-0" />
                      ) : (
                        <div className="w-5 h-5 rounded-full border-2 border-slate-200 shrink-0" />
                      )}
                      <span className={`text-sm font-medium ${isCompleted ? 'text-slate-900' : isActive ? 'text-indigo-700' : 'text-slate-400'}`}>
                        {stepMapping[stepKey].label}
                      </span>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>
          )}

          {appState === "success" && (
            <motion.div 
              key="success"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-xl mx-auto mt-24 bg-white rounded-[2rem] p-12 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] border border-slate-100 text-center"
            >
              <div className="w-20 h-20 bg-emerald-50 rounded-full mx-auto flex items-center justify-center mb-6">
                <Mail className="w-10 h-10 text-emerald-600" />
              </div>
              <h2 className="text-3xl font-bold text-slate-900 mb-4">Your audit is ready!</h2>
              <p className="text-slate-500 mb-8 text-lg">
                We've successfully generated your custom PDF report and emailed it to your inbox.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
                <button 
                  onClick={handleDownload}
                  className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-6 rounded-xl flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/20"
                >
                  <Download className="w-4 h-4" /> Download PDF Now
                </button>
                <button 
                  onClick={() => {
                    setAppState("idle");
                    setLeadId(null);
                    setFormData({name: "", email: "", company: "", website: "", industry: "", message: "", company_size: "Unknown"});
                  }}
                  className="w-full sm:w-auto bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium py-3 px-6 rounded-xl transition-all"
                >
                  Audit Another
                </button>
              </div>

              <div className="bg-slate-50 rounded-2xl p-6 text-left border border-slate-100">
                <h4 className="font-semibold text-slate-900 mb-3 text-sm uppercase tracking-wider">What's Inside:</h4>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <div className="mt-0.5 bg-white p-1 rounded-full shadow-sm border border-slate-100"><TrendingUp className="w-3.5 h-3.5 text-indigo-600" /></div>
                    <span className="text-slate-600 text-sm">Strategic Growth Opportunities</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="mt-0.5 bg-white p-1 rounded-full shadow-sm border border-slate-100"><Shield className="w-3.5 h-3.5 text-indigo-600" /></div>
                    <span className="text-slate-600 text-sm">Complete SWOT Analysis</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="mt-0.5 bg-white p-1 rounded-full shadow-sm border border-slate-100"><Zap className="w-3.5 h-3.5 text-indigo-600" /></div>
                    <span className="text-slate-600 text-sm">Technical & AI Automation Suggestions</span>
                  </li>
                </ul>
              </div>
            </motion.div>
          )}

          {appState === "error" && (
            <motion.div 
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-xl mx-auto mt-24 bg-white rounded-[2rem] p-12 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] border border-red-100 text-center"
            >
              <div className="w-20 h-20 bg-red-50 rounded-full mx-auto flex items-center justify-center mb-6">
                <Shield className="w-10 h-10 text-red-500" />
              </div>
              <h2 className="text-3xl font-bold text-slate-900 mb-4">Pipeline Error</h2>
              <p className="text-slate-500 mb-8 text-lg">
                {errorMessage}
              </p>
              <button 
                onClick={() => {
                  setAppState("idle");
                  setErrorMessage(null);
                }}
                className="bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 px-6 rounded-xl transition-all"
              >
                Go Back & Try Again
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
