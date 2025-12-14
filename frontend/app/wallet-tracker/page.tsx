"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Download, ChevronLeft } from "lucide-react"
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts"

export default function WalletTrackerPage() {
  const [walletInput, setWalletInput] = useState("")
  const [trackedWallets, setTrackedWallets] = useState([
    {
      id: 1,
      address: "0x7f3a8c2e9b1d4f6a5e8c2b9d1f4a7e3c",
      balance: "12.5 BTC",
      usdValue: "$487,500",
      risk: "CRITICAL",
      lastActivity: "2 min ago",
      transactions: 247,
      firstSeen: "2024-01-15",
      tags: ["ransomware", "darkweb"],
      tokens: [
        { symbol: "BTC", name: "Bitcoin", balance: "12.5", value: "$487,500", change: "+2.3%" },
        { symbol: "ETH", name: "Ethereum", balance: "45.8", value: "$156,240", change: "-1.2%" },
        { symbol: "USDC", name: "USD Coin", balance: "125000", value: "$125,000", change: "0%" },
      ],
    },
    {
      id: 2,
      address: "0x2b4e9f1a3c6d8e5f7a2b4c6d8e9f1a3c",
      balance: "45.8 ETH",
      usdValue: "$156,240",
      risk: "HIGH",
      lastActivity: "15 min ago",
      transactions: 89,
      firstSeen: "2024-02-20",
      tags: ["phishing", "scam"],
      tokens: [
        { symbol: "ETH", name: "Ethereum", balance: "45.8", value: "$156,240", change: "+1.5%" },
        { symbol: "DAI", name: "Dai", balance: "50000", value: "$50,000", change: "0%" },
      ],
    },
  ])

  const [selectedWallet, setSelectedWallet] = useState(trackedWallets[0])
  const [activeTab, setActiveTab] = useState("transactions")
  const [showDetailView, setShowDetailView] = useState(false)

  const handleAddWallet = () => {
    if (walletInput.trim()) {
      const newWallet = {
        id: trackedWallets.length + 1,
        address: walletInput,
        balance: `${Math.random() * 100}.${Math.floor(Math.random() * 99)} BTC`,
        usdValue: `$${Math.floor(Math.random() * 5000000)}`,
        risk: ["CRITICAL", "HIGH", "MEDIUM"][Math.floor(Math.random() * 3)],
        lastActivity: "Just now",
        transactions: Math.floor(Math.random() * 1000),
        firstSeen: new Date().toISOString().split("T")[0],
        tags: ["tracked"],
        tokens: [
          { symbol: "BTC", name: "Bitcoin", balance: "5.2", value: "$202,800", change: "+1.2%" },
          { symbol: "ETH", name: "Ethereum", balance: "25.3", value: "$86,520", change: "-0.8%" },
        ],
      }
      setTrackedWallets([...trackedWallets, newWallet])
      setSelectedWallet(newWallet)
      setWalletInput("")
    }
  }

  // Demo data for different tabs
  const transactionData = [
    { time: "20:45", value: 8.2 },
    { time: "04:00", value: 9.1 },
    { time: "08:00", value: 8.8 },
    { time: "12:00", value: 10.5 },
    { time: "16:00", value: 11.2 },
    { time: "20:00", value: 12.5 },
  ]

  const transactions = [
    {
      id: 1,
      signature: "5YLzpTA9CY99xQfX...",
      block: "375260924",
      time: "1 hr ago",
      instructions: "create",
      by: "DNHKNbf4JW...1ZvVhah827",
      value: "0.002061 SOL",
      fee: "0.00002232 SOL",
      programs: ["1+"],
      status: "confirmed",
    },
    {
      id: 2,
      signature: "4ZfAnsf4PVUENMJ...",
      block: "375258535",
      time: "2 hrs ago",
      instructions: "create",
      by: "DNHKNbf4JW...1ZvVhah827",
      value: "0.002061 SOL",
      fee: "0.00002232 SOL",
      programs: ["1+"],
      status: "confirmed",
    },
    {
      id: 3,
      signature: "jK14n9XnT5ZqCLtaX...",
      block: "375257572",
      time: "2 hrs ago",
      instructions: "transfer",
      by: "DNHKNbf4JW...1ZvVhah827",
      value: "0.000006331 SOL",
      fee: "0.000005 SOL",
      programs: ["3+"],
      status: "confirmed",
    },
  ]

  const transfers = [
    { id: 1, from: "0x7f3a...3c", to: "0x2b4e...3c", amount: "2.5 BTC", time: "1 hr ago", status: "confirmed" },
    { id: 2, from: "0x9d1e...8e", to: "0x5c8e...9f", amount: "15.3 ETH", time: "2 hrs ago", status: "confirmed" },
    { id: 3, from: "0x2b4e...3c", to: "0x7f3a...3c", amount: "8.7 BTC", time: "3 hrs ago", status: "confirmed" },
  ]

  const defiActivities = [
    { id: 1, protocol: "Uniswap", action: "Swap", amount: "10 ETH → 15000 USDC", time: "2 hrs ago", status: "success" },
    { id: 2, protocol: "Aave", action: "Deposit", amount: "50000 USDC", time: "5 hrs ago", status: "success" },
    {
      id: 3,
      protocol: "Curve",
      action: "Provide Liquidity",
      amount: "5 ETH + 10000 USDC",
      time: "1 day ago",
      status: "success",
    },
  ]

  const nftActivities = [
    {
      id: 1,
      collection: "Bored Ape Yacht Club",
      action: "Bought",
      tokenId: "#1234",
      price: "45 ETH",
      time: "3 days ago",
    },
    { id: 2, collection: "CryptoPunks", action: "Sold", tokenId: "#5678", price: "120 ETH", time: "1 week ago" },
  ]

  const balanceChanges = [
    { time: "2025-06-17", change: "+2.5 BTC", reason: "Incoming transfer", value: "12.5 BTC" },
    { time: "2025-06-16", change: "-1.2 BTC", reason: "Outgoing transfer", value: "10.0 BTC" },
    { time: "2025-06-15", change: "+0.8 BTC", reason: "Mining reward", value: "11.2 BTC" },
  ]

  const analyticsData = [
    { date: "Jun 10", inflow: 2.5, outflow: 1.2 },
    { date: "Jun 11", inflow: 3.1, outflow: 2.0 },
    { date: "Jun 12", inflow: 1.8, outflow: 3.5 },
    { date: "Jun 13", inflow: 4.2, outflow: 1.5 },
    { date: "Jun 14", inflow: 2.9, outflow: 2.8 },
    { date: "Jun 15", inflow: 3.5, outflow: 1.2 },
  ]

  const portfolio = [
    { asset: "Bitcoin", amount: "12.5", value: "$487,500", percentage: "65%" },
    { asset: "Ethereum", amount: "45.8", value: "$156,240", percentage: "21%" },
    { asset: "USDC", amount: "125000", value: "$125,000", percentage: "14%" },
  ]

  const stakeAccounts = [
    { validator: "Validator-001", amount: "32 ETH", reward: "0.85 ETH", status: "active" },
    { validator: "Validator-002", amount: "32 ETH", reward: "0.82 ETH", status: "active" },
  ]

  const domains = [
    { domain: "wallet.eth", owner: "0x7f3a...3c", expiry: "2026-01-15", status: "active" },
    { domain: "trader.eth", owner: "0x7f3a...3c", expiry: "2025-12-20", status: "active" },
  ]

  const cards = [
    { cardId: "****1234", type: "Visa", balance: "$5,000", status: "active" },
    { cardId: "****5678", type: "Mastercard", balance: "$2,500", status: "active" },
  ]

  const handleGenerateReport = () => {
    const reportContent = `
WALLET TRACKING REPORT
Generated: ${new Date().toLocaleString()}

WALLET ADDRESS: ${selectedWallet.address}
BALANCE: ${selectedWallet.balance} (${selectedWallet.usdValue})
RISK LEVEL: ${selectedWallet.risk}
TOTAL TRANSACTIONS: ${selectedWallet.transactions}
FIRST SEEN: ${selectedWallet.firstSeen}
LAST ACTIVITY: ${selectedWallet.lastActivity}

TAGS: ${selectedWallet.tags.join(", ")}

TOKEN HOLDINGS:
${selectedWallet.tokens.map((t) => `${t.symbol}: ${t.balance} (${t.value})`).join("\n")}

TRANSACTION HISTORY:
${transactions.map((tx) => `${tx.time} | ${tx.signature} | ${tx.value} | ${tx.status}`).join("\n")}

RISK ASSESSMENT:
- Transaction Frequency: High
- Mixing Service Usage: Detected
- Exchange Connections: Multiple
- Darkweb Activity: Confirmed
    `

    const element = document.createElement("a")
    element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(reportContent))
    element.setAttribute("download", `wallet-report-${selectedWallet.address.slice(0, 8)}.txt`)
    element.style.display = "none"
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  if (showDetailView) {
    return (
      <div className="p-6 space-y-6">
        {/* Header with back button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => setShowDetailView(false)}
              className="bg-orange-500 hover:bg-orange-600 text-black h-9"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Back
            </Button>
            <div>
              <h2 className="text-2xl font-bold text-orange-400">WALLET DETAILS</h2>
              <p className="text-sm text-neutral-500 mt-1 font-mono">{selectedWallet.address}</p>
            </div>
          </div>
          <Button onClick={handleGenerateReport} className="bg-orange-500 hover:bg-orange-600 text-black">
            <Download className="w-4 h-4 mr-2" />
            Generate Report
          </Button>
        </div>

        {/* Wallet Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-neutral-900 border-orange-900/30">
            <CardContent className="pt-6">
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Balance</p>
              <p className="text-2xl font-bold text-orange-400 font-mono">{selectedWallet.balance}</p>
              <p className="text-xs text-neutral-500 mt-1">{selectedWallet.usdValue}</p>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-orange-900/30">
            <CardContent className="pt-6">
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Risk Level</p>
              <span
                className={`text-lg font-bold px-2 py-1 rounded inline-block ${
                  selectedWallet.risk === "CRITICAL"
                    ? "bg-red-500/20 text-red-400"
                    : selectedWallet.risk === "HIGH"
                      ? "bg-orange-500/20 text-orange-400"
                      : "bg-yellow-500/20 text-yellow-400"
                }`}
              >
                {selectedWallet.risk}
              </span>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-orange-900/30">
            <CardContent className="pt-6">
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Transactions</p>
              <p className="text-2xl font-bold text-orange-400 font-mono">{selectedWallet.transactions}</p>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-orange-900/30">
            <CardContent className="pt-6">
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Last Activity</p>
              <p className="text-sm text-neutral-400">{selectedWallet.lastActivity}</p>
            </CardContent>
          </Card>
        </div>

        {/* Wallet Info */}
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">WALLET INFORMATION</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">First Seen</p>
                <p className="text-sm text-neutral-400">{selectedWallet.firstSeen}</p>
              </div>
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Last Activity</p>
                <p className="text-sm text-neutral-400">{selectedWallet.lastActivity}</p>
              </div>
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Total Value</p>
                <p className="text-sm text-orange-400 font-mono">{selectedWallet.usdValue}</p>
              </div>
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Status</p>
                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded inline-block">Active</span>
              </div>
            </div>

            {/* Tags */}
            <div>
              <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Tags</p>
              <div className="flex flex-wrap gap-2">
                {selectedWallet.tags.map((tag) => (
                  <span key={tag} className="text-xs bg-orange-500/20 text-orange-400 px-2 py-1 rounded">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tab Navigation */}
        <div className="flex gap-2 overflow-x-auto pb-2 border-b border-neutral-800">
          {[
            { id: "transactions", label: "Transactions" },
            { id: "transfers", label: "Transfers" },
            { id: "defi", label: "DeFi Activities" },
            { id: "nft", label: "NFT Activities" },
            { id: "balance", label: "Balance Changes" },
            { id: "analytics", label: "Analytics" },
            { id: "portfolio", label: "Portfolio" },
            { id: "stake", label: "Stake Accounts" },
            { id: "domains", label: "Domains" },
            { id: "cards", label: "Cards" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? "text-orange-400 border-b-2 border-orange-400"
                  : "text-neutral-500 hover:text-neutral-400"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div>
          {/* Transactions Tab */}
          {activeTab === "transactions" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">
                  TRANSACTION HISTORY
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">SIGNATURE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">BLOCK</th>
                        <th className="text-left py-2 px-2 text-neutral-500">TIME</th>
                        <th className="text-left py-2 px-2 text-neutral-500">INSTRUCTIONS</th>
                        <th className="text-left py-2 px-2 text-neutral-500">VALUE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">FEE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx) => (
                        <tr key={tx.id} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-orange-400 font-mono cursor-pointer hover:text-orange-300">
                            {tx.signature}
                          </td>
                          <td className="py-2 px-2 text-neutral-400 font-mono">{tx.block}</td>
                          <td className="py-2 px-2 text-neutral-400">{tx.time}</td>
                          <td className="py-2 px-2 text-neutral-400">{tx.instructions}</td>
                          <td className="py-2 px-2 text-white font-mono">{tx.value}</td>
                          <td className="py-2 px-2 text-neutral-400">{tx.fee}</td>
                          <td className="py-2 px-2">
                            <span className="px-2 py-1 rounded text-xs font-bold bg-green-500/20 text-green-400">
                              {tx.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Transfers Tab */}
          {activeTab === "transfers" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">TRANSFER HISTORY</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">FROM</th>
                        <th className="text-left py-2 px-2 text-neutral-500">TO</th>
                        <th className="text-left py-2 px-2 text-neutral-500">AMOUNT</th>
                        <th className="text-left py-2 px-2 text-neutral-500">TIME</th>
                        <th className="text-left py-2 px-2 text-neutral-500">STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transfers.map((tx) => (
                        <tr key={tx.id} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-orange-400 font-mono">{tx.from}</td>
                          <td className="py-2 px-2 text-orange-400 font-mono">{tx.to}</td>
                          <td className="py-2 px-2 text-white font-mono">{tx.amount}</td>
                          <td className="py-2 px-2 text-neutral-400">{tx.time}</td>
                          <td className="py-2 px-2">
                            <span className="px-2 py-1 rounded text-xs font-bold bg-green-500/20 text-green-400">
                              {tx.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* DeFi Activities Tab */}
          {activeTab === "defi" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">DEFI ACTIVITIES</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">PROTOCOL</th>
                        <th className="text-left py-2 px-2 text-neutral-500">ACTION</th>
                        <th className="text-left py-2 px-2 text-neutral-500">AMOUNT</th>
                        <th className="text-left py-2 px-2 text-neutral-500">TIME</th>
                        <th className="text-left py-2 px-2 text-neutral-500">STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {defiActivities.map((activity) => (
                        <tr key={activity.id} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-orange-400 font-mono">{activity.protocol}</td>
                          <td className="py-2 px-2 text-neutral-400">{activity.action}</td>
                          <td className="py-2 px-2 text-white font-mono">{activity.amount}</td>
                          <td className="py-2 px-2 text-neutral-400">{activity.time}</td>
                          <td className="py-2 px-2">
                            <span className="px-2 py-1 rounded text-xs font-bold bg-green-500/20 text-green-400">
                              {activity.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* NFT Activities Tab */}
          {activeTab === "nft" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">NFT ACTIVITIES</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">COLLECTION</th>
                        <th className="text-left py-2 px-2 text-neutral-500">ACTION</th>
                        <th className="text-left py-2 px-2 text-neutral-500">TOKEN ID</th>
                        <th className="text-left py-2 px-2 text-neutral-500">PRICE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">TIME</th>
                      </tr>
                    </thead>
                    <tbody>
                      {nftActivities.map((activity) => (
                        <tr key={activity.id} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-orange-400">{activity.collection}</td>
                          <td className="py-2 px-2 text-neutral-400">{activity.action}</td>
                          <td className="py-2 px-2 text-neutral-400 font-mono">{activity.tokenId}</td>
                          <td className="py-2 px-2 text-white font-mono">{activity.price}</td>
                          <td className="py-2 px-2 text-neutral-400">{activity.time}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Balance Changes Tab */}
          {activeTab === "balance" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">BALANCE CHANGES</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">DATE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">CHANGE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">REASON</th>
                        <th className="text-left py-2 px-2 text-neutral-500">BALANCE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {balanceChanges.map((change, idx) => (
                        <tr key={idx} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-neutral-400">{change.time}</td>
                          <td
                            className={`py-2 px-2 font-mono ${change.change.startsWith("+") ? "text-green-400" : "text-red-400"}`}
                          >
                            {change.change}
                          </td>
                          <td className="py-2 px-2 text-neutral-400">{change.reason}</td>
                          <td className="py-2 px-2 text-white font-mono">{change.value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Analytics Tab */}
          {activeTab === "analytics" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">
                  INFLOW/OUTFLOW ANALYTICS
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analyticsData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="date" stroke="#666" />
                    <YAxis stroke="#666" />
                    <Tooltip contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #FF6B35" }} />
                    <Bar dataKey="inflow" fill="#FF6B35" name="Inflow" />
                    <Bar dataKey="outflow" fill="#ef4444" name="Outflow" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Portfolio Tab */}
          {activeTab === "portfolio" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">
                  PORTFOLIO BREAKDOWN
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">ASSET</th>
                        <th className="text-left py-2 px-2 text-neutral-500">AMOUNT</th>
                        <th className="text-left py-2 px-2 text-neutral-500">VALUE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">PERCENTAGE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.map((item, idx) => (
                        <tr key={idx} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-orange-400">{item.asset}</td>
                          <td className="py-2 px-2 text-neutral-400 font-mono">{item.amount}</td>
                          <td className="py-2 px-2 text-white font-mono">{item.value}</td>
                          <td className="py-2 px-2">
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-2 bg-neutral-700 rounded overflow-hidden">
                                <div className="h-full bg-orange-500" style={{ width: item.percentage }} />
                              </div>
                              <span className="text-neutral-400">{item.percentage}</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Stake Accounts Tab */}
          {activeTab === "stake" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">STAKE ACCOUNTS</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">VALIDATOR</th>
                        <th className="text-left py-2 px-2 text-neutral-500">AMOUNT</th>
                        <th className="text-left py-2 px-2 text-neutral-500">REWARD</th>
                        <th className="text-left py-2 px-2 text-neutral-500">STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stakeAccounts.map((account, idx) => (
                        <tr key={idx} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-orange-400">{account.validator}</td>
                          <td className="py-2 px-2 text-neutral-400 font-mono">{account.amount}</td>
                          <td className="py-2 px-2 text-white font-mono">{account.reward}</td>
                          <td className="py-2 px-2">
                            <span className="px-2 py-1 rounded text-xs font-bold bg-green-500/20 text-green-400">
                              {account.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Domains Tab */}
          {activeTab === "domains" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">DOMAINS</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">DOMAIN</th>
                        <th className="text-left py-2 px-2 text-neutral-500">OWNER</th>
                        <th className="text-left py-2 px-2 text-neutral-500">EXPIRY</th>
                        <th className="text-left py-2 px-2 text-neutral-500">STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {domains.map((domain, idx) => (
                        <tr key={idx} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-orange-400">{domain.domain}</td>
                          <td className="py-2 px-2 text-neutral-400 font-mono">{domain.owner}</td>
                          <td className="py-2 px-2 text-neutral-400">{domain.expiry}</td>
                          <td className="py-2 px-2">
                            <span className="px-2 py-1 rounded text-xs font-bold bg-green-500/20 text-green-400">
                              {domain.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Cards Tab */}
          {activeTab === "cards" && (
            <Card className="bg-neutral-900 border-orange-900/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">CARDS</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-neutral-700">
                        <th className="text-left py-2 px-2 text-neutral-500">CARD ID</th>
                        <th className="text-left py-2 px-2 text-neutral-500">TYPE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">BALANCE</th>
                        <th className="text-left py-2 px-2 text-neutral-500">STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cards.map((card, idx) => (
                        <tr key={idx} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                          <td className="py-2 px-2 text-orange-400 font-mono">{card.cardId}</td>
                          <td className="py-2 px-2 text-neutral-400">{card.type}</td>
                          <td className="py-2 px-2 text-white font-mono">{card.balance}</td>
                          <td className="py-2 px-2">
                            <span className="px-2 py-1 rounded text-xs font-bold bg-green-500/20 text-green-400">
                              {card.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">CRYPTO WALLET TRACKER</h2>
          <p className="text-sm text-neutral-500 mt-1">
            Monitor illicit cryptocurrency transactions and wallet activity
          </p>
        </div>
      </div>

      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">ADD WALLET TO TRACK</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter wallet address (0x...)"
              value={walletInput}
              onChange={(e) => setWalletInput(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleAddWallet()}
              className="flex-1 px-4 py-2 bg-neutral-800 border border-neutral-700 rounded text-white placeholder-neutral-500 focus:outline-none focus:border-orange-500"
            />
            <Button onClick={handleAddWallet} className="bg-orange-500 hover:bg-orange-600 text-black">
              <Plus className="w-4 h-4 mr-2" />
              Track Wallet
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Wallet Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Wallets Tracked</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">{trackedWallets.length}</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Total Holdings</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">847.3 BTC</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">24h Transactions</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">1,247</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">High Risk</p>
            <p className="text-3xl font-bold text-red-400 font-mono">
              {trackedWallets.filter((w) => w.risk === "CRITICAL").length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Wallet List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card className="bg-neutral-900 border-orange-900/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">TRACKED WALLETS</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {trackedWallets.map((wallet) => (
                  <div
                    key={wallet.id}
                    onClick={() => {
                      setSelectedWallet(wallet)
                      setShowDetailView(true)
                      setActiveTab("transactions")
                    }}
                    className="p-3 rounded cursor-pointer transition-colors bg-neutral-800 border border-neutral-700 hover:border-orange-500/50 hover:bg-neutral-800/80"
                  >
                    <p className="text-xs text-orange-400 font-mono truncate">{wallet.address}</p>
                    <p className="text-xs text-neutral-400 mt-1">{wallet.balance}</p>
                    <div className="flex justify-between items-center mt-2">
                      <span
                        className={`text-xs font-bold px-2 py-0.5 rounded ${
                          wallet.risk === "CRITICAL"
                            ? "bg-red-500/20 text-red-400"
                            : wallet.risk === "HIGH"
                              ? "bg-orange-500/20 text-orange-400"
                              : "bg-yellow-500/20 text-yellow-400"
                        }`}
                      >
                        {wallet.risk}
                      </span>
                      <span className="text-xs text-neutral-500">{wallet.transactions} txs</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Token Holdings */}
        <div className="lg:col-span-2">
          <Card className="bg-neutral-900 border-orange-900/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">TOKEN HOLDINGS</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-neutral-700">
                      <th className="text-left py-2 px-2 text-neutral-500">SYMBOL</th>
                      <th className="text-left py-2 px-2 text-neutral-500">NAME</th>
                      <th className="text-left py-2 px-2 text-neutral-500">BALANCE</th>
                      <th className="text-left py-2 px-2 text-neutral-500">VALUE</th>
                      <th className="text-left py-2 px-2 text-neutral-500">CHANGE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedWallet.tokens.map((token, idx) => (
                      <tr key={idx} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                        <td className="py-2 px-2 text-orange-400 font-mono">{token.symbol}</td>
                        <td className="py-2 px-2 text-neutral-400">{token.name}</td>
                        <td className="py-2 px-2 text-white font-mono">{token.balance}</td>
                        <td className="py-2 px-2 text-white font-mono">{token.value}</td>
                        <td
                          className={`py-2 px-2 font-mono ${token.change.startsWith("+") ? "text-green-400" : "text-red-400"}`}
                        >
                          {token.change}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
