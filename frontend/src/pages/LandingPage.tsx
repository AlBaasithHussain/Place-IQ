import Cta from "../components/Cta";
import Features from "../components/Features";
import Footer from "../components/Footer";
import Hero from "../components/Hero";
import HowItWorks from "../components/HowItWorks";
import Navbar from "../components/Navbar";
import Roadmap from "../components/Roadmap";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <Roadmap />
        <Cta />
      </main>
      <Footer />
    </div>
  );
}
