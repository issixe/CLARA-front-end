"use client";

import Link from "next/link";
import Image from "next/image";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown, User, Settings, LogOut } from "lucide-react";

export function Navigation() {
  return (
    <nav className="fixed top-0 left-0 right-0 bg-white/90 backdrop-blur-sm border-b border-gray-200 z-50">
      <div className="flex justify-between items-center px-6 py-2">
        <div className="flex items-center">
          <Image
            src="/clara_logo.png"
            alt="CLARA Logo"
            width={48}
            height={48}
          />
          <h1
            className="font-agbalumo text-4xl ml-3"
            style={{ color: "#F5CC98" }}
          >
            CLARA
          </h1>
        </div>

        {/* Navigation Items */}
        <div className="flex items-center space-x-8">
          <Link
            href="/"
            className="text-gray-700 hover:text-[#F099C1] font-medium transition-colors"
          >
            Home
          </Link>

          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center text-gray-700 hover:text-[#F099C1] font-medium transition-colors">
              Transcripts
              <ChevronDown className="ml-1 h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <Link href="/logs">
                <DropdownMenuItem>Logs</DropdownMenuItem>
              </Link>
              <Link href="/reports">
                <DropdownMenuItem>Reports</DropdownMenuItem>
              </Link>
            </DropdownMenuContent>
          </DropdownMenu>

          <Link
            href="/contacts"
            className="text-gray-700 hover:text-[#F099C1] font-medium transition-colors"
          >
            My People
          </Link>

          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center justify-center w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 transition-colors">
              <User className="h-5 w-5 text-gray-600" />
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem className="flex items-center">
                <Settings className="mr-2 h-4 w-4" />
                Manage
              </DropdownMenuItem>
              <DropdownMenuItem
                className="flex items-center transition-colors"
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "#fef2f2";
                  e.currentTarget.style.color = "#dc2626";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "";
                  e.currentTarget.style.color = "";
                }}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Log Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </nav>
  );
}
