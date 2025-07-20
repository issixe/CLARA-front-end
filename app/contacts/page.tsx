"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Plus,
  Trash2,
  ChevronDown,
  User,
  Settings,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Contact {
  id: number;
  name: string;
  email: string;
  phone: string;
}

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([
    {
      id: 1,
      name: "Dr. Sarah Johnson",
      email: "sarah.johnson@hospital.com",
      phone: "(416) 123-4567",
    },
    {
      id: 2,
      name: "Dr. Michael Chen",
      email: "m.chen@clinic.com",
      phone: "(647) 987-6543",
    },
    {
      id: 3,
      name: "Mary Shelley",
      email: "mary.shelly@gmail.com",
      phone: "(416) 456-7890",
    },
  ]);

  const [newContact, setNewContact] = useState({
    name: "",
    email: "",
    phone: "",
  });
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const addContact = () => {
    if (newContact.name && newContact.email && newContact.phone) {
      const contact: Contact = {
        id: Date.now(),
        ...newContact,
      };
      setContacts([...contacts, contact]);
      setNewContact({ name: "", email: "", phone: "" });
      setIsDialogOpen(false);
    }
  };

  const removeContact = (id: number) => {
    setContacts(contacts.filter((contact) => contact.id !== id));
  };

  return (
    <div className="min-h-screen p-6 bg-[#fff3e2]">
      {/* Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 bg-white/90 backdrop-blur-sm border-b border-gray-200 z-50">
        <div className="flex justify-between items-center px-6 py-2">
          <div className="flex items-center">
            <img
              src="/clara_logo.png"
              alt="CLARA Logo"
              className="h-12 w-auto"
            />
            <h1
              className="font-agbalumo text-4xl text-gray-800 ml-3"
              style={{
                color: "#F5CC98",
              }}
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

      {/* Main Content with top padding for nav */}
      <div className="pt-24">
        {/* Add Contact Button */}
        <div className="flex justify-end mb-8">
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#F099C1] hover:bg-[#EA83B3] text-white font-semibold py-3 px-8 rounded-2xl transition-colors">
                <Plus className="h-5 w-5 mr-2" />
                Add Contact
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-white rounded-2xl">
              <DialogHeader>
                <DialogTitle className="text-2xl font-bold text-gray-800">
                  Add New Contact
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="name" className="text-gray-700">
                    Name
                  </Label>
                  <Input
                    id="name"
                    value={newContact.name}
                    onChange={(e) =>
                      setNewContact({ ...newContact, name: e.target.value })
                    }
                    className="rounded-xl border-gray-300"
                    placeholder="Enter full name"
                  />
                </div>
                <div>
                  <Label htmlFor="email" className="text-gray-700">
                    Email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={newContact.email}
                    onChange={(e) =>
                      setNewContact({ ...newContact, email: e.target.value })
                    }
                    className="rounded-xl border-gray-300"
                    placeholder="Enter email address"
                  />
                </div>
                <div>
                  <Label htmlFor="phone" className="text-gray-700">
                    Phone Number
                  </Label>
                  <Input
                    id="phone"
                    value={newContact.phone}
                    onChange={(e) =>
                      setNewContact({ ...newContact, phone: e.target.value })
                    }
                    className="rounded-xl border-gray-300"
                    placeholder="Enter phone number"
                  />
                </div>
                <Button
                  onClick={addContact}
                  className="w-full bg-[#F099C1] hover:bg-[#EA83B3] text-white font-semibold py-2 rounded-xl"
                >
                  Add Contact
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Contacts List */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {contacts.map((contact) => (
            <Card
              key={contact.id}
              className="bg-white/80 backdrop-blur-sm border-none rounded-2xl shadow-lg"
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xl font-semibold text-gray-800">
                  {contact.name}
                </CardTitle>
                <div className="flex space-x-2">
                  <Button variant="ghost" size="icon" className="bg-white/80">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-4 w-4 fill-current"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      xmlns="http://www.w3.org/2000/svg" width="800px"
                      height="800px" viewBox="0 0 24 24"
                      id="_24x24_On_Light_Edit" data-name="24x24/On Light/Edit"
                      <rect id="view-box" width="24" height="24" fill="none" />
                      <path
                        id="Shape"
                        d="M.75,17.5A.751.751,0,0,1,0,16.75V12.569a.755.755,0,0,1,.22-.53L11.461.8a2.72,2.72,0,0,1,3.848,0L16.7,2.191a2.72,2.72,0,0,1,0,3.848L5.462,17.28a.747.747,0,0,1-.531.22ZM1.5,12.879V16h3.12l7.91-7.91L9.41,4.97ZM13.591,7.03l2.051-2.051a1.223,1.223,0,0,0,0-1.727L14.249,1.858a1.222,1.222,0,0,0-1.727,0L10.47,3.91Z"
                        transform="translate(3.25 3.25)"
                        fill="#141124"
                      />
                    </svg>
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeContact(contact.id)}
                    className="text-red-500 hover:bg-red-50 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <p className="text-gray-800">{contact.email}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Phone</p>
                  <p className="text-gray-800">{contact.phone}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {contacts.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-600 text-lg">No contacts added yet.</p>
            <p className="text-gray-500">Click "Add Contact" to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
}
