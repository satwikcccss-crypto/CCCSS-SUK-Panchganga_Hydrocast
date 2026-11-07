"use client";

import React from "react";
import { ShieldCheck, Award, Building2, Users, FileLock2, AlertCircle, Info, ExternalLink } from "lucide-react";

export default function ProjectInfoPanel() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-in fade-in duration-500">
      {/* ── TOP HERO BANNER ─────────────────────────────────────────── */}
      <div className="relative overflow-hidden bg-gradient-to-r from-slate-900 via-sky-950 to-indigo-950 rounded-xl p-6 sm:p-8 text-white shadow-md border border-slate-800">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className="px-2.5 py-1 text-[11px] font-bold tracking-wider uppercase rounded-full bg-sky-500/20 text-sky-300 border border-sky-400/30">
              DST-SERB Sponsored Research Project
            </span>
            <span className="px-2.5 py-1 text-[11px] font-bold tracking-wider uppercase rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
              Shivaji University, Kolhapur
            </span>
            <span className="px-2.5 py-1 text-[11px] font-bold tracking-wider uppercase rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
              CCCSS Initiative
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2">
            IoT and Geoinformatics-Based Flood Monitoring & Prediction System
          </h1>
          <p className="text-sm sm:text-base text-slate-300 max-w-3xl leading-relaxed">
            High-precision operational hydrological simulation, real-time ultrasonic river gauge telemetry, 
            and AI-adaptive stage forecasting for the Panchganga River Basin in Kolhapur, Maharashtra.
          </p>
        </div>
      </div>

      {/* ── GRID OF CORE PROJECT DETAILS ────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Card 1: Funding Agency */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow">
          <div>
            <div className="w-10 h-10 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center mb-4 border border-sky-100">
              <Award className="w-5 h-5" />
            </div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Funding & Sponsoring Body
            </h2>
            <h3 className="text-lg font-bold text-slate-900 mb-2">
              DST-SERB
            </h3>
            <p className="text-sm font-medium text-slate-700 mb-2">
              Department of Science and Technology – Science and Engineering Research Board
            </p>
            <p className="text-xs text-slate-500 leading-normal">
              Statutory body under the Department of Science and Technology, Government of India, supporting advanced scientific research and technological innovation.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs font-semibold text-sky-700 flex items-center gap-1">
            <span>Govt. of India Research Grant</span>
          </div>
        </div>

        {/* Card 2: Host Institution */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow">
          <div>
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center mb-4 border border-indigo-100">
              <Building2 className="w-5 h-5" />
            </div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Host Academic Institution
            </h2>
            <h3 className="text-lg font-bold text-slate-900 mb-2">
              Shivaji University, Kolhapur
            </h3>
            <p className="text-sm font-medium text-slate-700 mb-2">
              Centre for Climate Change and Sustainability Studies (CCCSS)
            </p>
            <p className="text-xs text-slate-500 leading-normal">
              A premier NAAC A++ accredited state university in Maharashtra, India. This system represents the collective research effort of resource persons across Geography, Electronics, and Allied Sciences.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs font-semibold text-indigo-700 flex items-center gap-1">
            <span>Kolhapur - 416004, Maharashtra</span>
          </div>
        </div>

        {/* Card 3: Project Leadership */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs flex flex-col justify-between hover:shadow-md transition-shadow">
          <div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center mb-4 border border-emerald-100">
              <Users className="w-5 h-5" />
            </div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Project Leadership & Team
            </h2>
            <h3 className="text-lg font-bold text-slate-900 mb-2">
              Investigators & Developers
            </h3>
            <div className="space-y-2.5 text-xs">
              <div>
                <span className="font-semibold text-slate-900 block text-[13px]">
                  Dr. Sachin S. Panhalkar
                </span>
                <span className="text-slate-500 font-medium">
                  Principal Investigator (PI)
                </span>
              </div>
              <div>
                <span className="font-semibold text-slate-900 block text-[13px]">
                  Dr. Ganesh S. Nhivekar
                </span>
                <span className="text-slate-500 font-medium">
                  Co-Principal Investigator (Co-PI)
                </span>
              </div>
              <div className="pt-1 border-t border-slate-100">
                <span className="font-semibold text-sky-900 block text-[13px]">
                  Er. Satwik K. Udupi
                </span>
                <span className="text-slate-500 font-medium">
                  System Architecture & Full-Stack Development
                </span>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs font-semibold text-emerald-700 flex items-center gap-1">
            <span>Research & Engineering Core</span>
          </div>
        </div>
      </div>

      {/* ── SYSTEM MANDATE & DATA RIGHTS ────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Mission & Purpose */}
        <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-md bg-blue-50 text-blue-700 border border-blue-100">
              <Info className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                System Mission & Public Service
              </h2>
              <p className="text-xs text-slate-500">Citizen Early Warning & Basin Intelligence</p>
            </div>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed mb-3">
            This system is engineered to alert the citizens, civic planners, and emergency responders 
            of Kolhapur regarding current and future flood stages in the Panchganga River system.
          </p>
          <ul className="text-xs text-slate-600 space-y-2 list-disc list-inside">
            <li>
              Real-time ultrasonic stage telemetry continuously captured at <strong className="text-slate-800">Chhatrapati Shivaji Maharaj Bridge</strong> (urban sink).
            </li>
            <li>
              Automated 90-hour ECMWF forecast hyetograph routing across <strong className="text-slate-800">9 delineated subbasins (S1–S9)</strong>.
            </li>
            <li>
              Predictive flood peak arrival timelines with 95% confidence intervals at <strong className="text-slate-800">Rajaram K.T. Weir</strong> and Shivaji Bridge.
            </li>
          </ul>
        </div>

        {/* Data Rights & Unauthorized Access Notice */}
        <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 rounded-md bg-rose-50 text-rose-700 border border-rose-100">
              <FileLock2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Data System Rights & Security Notice
              </h2>
              <p className="text-xs text-slate-500">Institutional Ownership & Protection</p>
            </div>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed mb-3">
            All data systems, algorithmic pipelines, calibration records, and software assets 
            are the exclusive intellectual property of <strong className="text-slate-900">Shivaji University, Kolhapur</strong>.
          </p>
          <div className="p-3 bg-rose-50/70 border border-rose-200 rounded-md text-xs text-rose-900 space-y-1">
            <p className="font-bold flex items-center gap-1.5 text-rose-800">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              Unauthorized Access Prohibited
            </p>
            <p>
              Unauthorized access, reproduction, commercial scraping, or reverse engineering of this portal 
              and its underlying databases is strictly prohibited under institutional IP policies and Indian Cyber Law.
            </p>
          </div>
        </div>
      </div>

      {/* ── LEGAL & RESEARCH DISCLAIMER ─────────────────────────────── */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-5 flex items-start gap-3 text-amber-900 text-xs sm:text-sm">
        <AlertCircle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h2 className="font-bold text-amber-900">
            Advisory Notice: Information and Research Purpose Only
          </h2>
          <p className="text-xs text-amber-800 leading-relaxed">
            This platform operates as an advanced scientific decision-support and research system. All predictions, 
            water levels, and discharge projections are issued for information and research purposes only. 
            Official flood declarations, inundation bulletins, and statutory evacuation orders remain under the 
            sole jurisdiction of the <strong>District Disaster Management Authority (DDMA), Kolhapur</strong>, 
            the <strong>Water Resources Department (WRD)</strong>, and the <strong>Central Water Commission (CWC)</strong>.
          </p>
        </div>
      </div>
    </div>
  );
}
