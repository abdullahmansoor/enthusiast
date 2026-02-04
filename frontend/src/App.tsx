import './App.css'
import { Outlet } from "react-router-dom";
import { ApplicationContextProvider } from "@/components/util/application-context-provider.tsx";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar.tsx";
import { MainSidebar } from "@/components/navigation/main-sidebar.tsx";
import { Toaster } from "@/components/ui/toaster";

function App() {
  return (
    <ApplicationContextProvider>
      <SidebarProvider>
        <MainSidebar />
        <SidebarInset>
        <div className="flex flex-col grow">
          <Outlet/>
        </div>
        </SidebarInset>
      </SidebarProvider>
      <Toaster />
    </ApplicationContextProvider>
  )
}

export default App
