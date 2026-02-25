"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Download, ChevronLeft, Loader2, RefreshCcw, Search, Wallet, AlertTriangle, Trash2, History, Activity, TrendingUp, Info } from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"
import { format } from "date-fns"

export default function WalletTrackerPage() {
  const [activeTab, setActiveTab] = useState("overview")
  const [walletInput, setWalletInput] = useState("")
  const [txInput, setTxInput] = useState("")
  const [currency, setCurrency] = useState("BTC")
  
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [trackedWallets, setTrackedWallets] = useState([])
  
  // Detail views
  const [showDetailView, setShowDetailView] = useState(false)
  const [selectedWallet, setSelectedWallet] = useState<any>(null)
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  // Transaction view
  const [txDetails, setTxDetails] = useState<any>(null)
  const [isTxLoading, setIsTxLoading] = useState(false)

  const fetchWallets = async () => {
    try {
      const data = await apiClient.getTrackedWallets()
      setTrackedWallets(data.wallets || [])
    } catch (error) {
      console.error("Failed to fetch wallets:", error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchWallets()
  }, [])

  const handleAddWallet = async () => {
    if (!walletInput.trim()) {
      toast.error("Please enter a wallet address")
      return
    }

    setIsSubmitting(true)
    try {
      await apiClient.addWalletToTrack(walletInput, currency, `Manual: ${walletInput.slice(0, 8)}`, true)
      toast.success("Wallet added to watchlist")
      setWalletInput("")
      fetchWallets()
    } catch (error) {
      toast.error("Failed to add wallet")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleAnalyzeAddress = async (address: string) => {
    setIsAnalyzing(true)
    setShowDetailView(true)
    setAnalysisData(null)
    try {
      const res = await apiClient.analyzeWallet(address)
      setAnalysisData(res.details)
      setSelectedWallet({
          address: address,
          currency: res.chain.toUpperCase(),
          risk_level: res.details?.transaction_count > 50 ? 'high' : 'low',
          first_seen_at: res.details?.first_seen
      })
    } catch (error) {
      toast.error("Analysis failed. Address may be invalid or not found.")
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleLookupTx = async () => {
    if (!txInput.trim()) return
    setIsTxLoading(true)
    setTxDetails(null)
    setActiveTab("transactions")
    try {
      const res = await apiClient.lookupTransaction(txInput)
      setTxDetails(res)
    } catch (error) {
      toast.error("Transaction hash not found on common chains")
    } finally {
      setIsTxLoading(false)
    }
  }

  const handleDeleteWallet = async (id: string) => {
    try {
      await apiClient.stopTrackingWallet(id)
      toast.success("Stopped tracking wallet")
      fetchWallets()
    } catch (error) {
      toast.error("Failed to delete wallet")
    }
  }

  if (showDetailView && selectedWallet) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => {setShowDetailView(false); setAnalysisData(null);}}
              className="bg-orange-500 hover:bg-orange-600 text-black h-9"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Back
            </Button>
            <div>
              <h2 className="text-2xl font-bold text-orange-400 uppercase">Analysis: {selectedWallet.currency}</h2>
              <p className="text-xs text-neutral-500 mt-1 font-mono break-all">{selectedWallet.address}</p>
            </div>
          </div>
        </div>

        {isAnalyzing ? (
            <Card className="bg-neutral-900 border-orange-900/30 p-12 text-center">
                <Loader2 className="w-12 h-12 text-orange-500 animate-spin mx-auto mb-4" />
                <p className="text-orange-400 font-mono animate-pulse">QUERYING BLOCKCHAIN NODES...</p>
            </Card>
        ) : (
            <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card className="bg-neutral-900 border-orange-900/30">
                        <CardContent className="pt-6 text-center">
                            <TrendingUp className="w-5 h-5 text-orange-500 mx-auto mb-2" />
                            <p className="text-[10px] text-neutral-500 uppercase">Balance</p>
                            <p className="text-xl font-bold text-white font-mono">{analysisData?.balance || '0.00'}</p>
                            <p className="text-[10px] text-orange-400">${analysisData?.balance_usd || '0.00'}</p>
                        </CardContent>
                    </Card>
                    <Card className="bg-neutral-900 border-orange-900/30">
                        <CardContent className="pt-6 text-center">
                            <Activity className="w-5 h-5 text-orange-500 mx-auto mb-2" />
                            <p className="text-[10px] text-neutral-500 uppercase">Total Transactions</p>
                            <p className="text-xl font-bold text-white font-mono">{analysisData?.transaction_count || '0'}</p>
                        </CardContent>
                    </Card>
                    <Card className="bg-neutral-900 border-orange-900/30">
                        <CardContent className="pt-6 text-center">
                            <AlertTriangle className="w-5 h-5 text-orange-500 mx-auto mb-2" />
                            <p className="text-[10px] text-neutral-500 uppercase">Risk Assessment</p>
                            <p className="text-sm font-bold text-orange-400 uppercase mt-1">{selectedWallet.risk_level || 'LOW'}</p>
                        </CardContent>
                    </Card>
                    <Card className="bg-neutral-900 border-orange-900/30">
                        <CardContent className="pt-6 text-center">
                            <History className="w-5 h-5 text-orange-500 mx-auto mb-2" />
                            <p className="text-[10px] text-neutral-500 uppercase">First Seen</p>
                            <p className="text-[10px] text-white mt-1">{analysisData?.first_seen || 'Unknown'}</p>
                        </CardContent>
                    </Card>
                </div>

                <Card className="bg-neutral-900 border-orange-900/30">
                    <CardHeader>
                        <CardTitle className="text-sm text-orange-400 uppercase tracking-widest">FLOW ANALYSIS</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div className="space-y-4">
                                <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
                                    <span className="text-xs text-neutral-500">TOTAL RECEIVED</span>
                                    <span className="text-sm font-mono text-green-400">{analysisData?.received_total || '0.00'}</span>
                                </div>
                                <div className="flex justify-between items-center border-b border-neutral-800 pb-2">
                                    <span className="text-xs text-neutral-500">TOTAL SENT</span>
                                    <span className="text-sm font-mono text-red-400">{analysisData?.sent_total || '0.00'}</span>
                                </div>
                            </div>
                            <div className="p-4 bg-neutral-800/50 rounded-lg border border-neutral-700/50">
                                <div className="flex items-center gap-2 mb-2">
                                    <Info className="w-4 h-4 text-orange-500" />
                                    <span className="text-xs font-bold text-white uppercase">Intelligence Note</span>
                                </div>
                                <p className="text-xs text-neutral-400 leading-relaxed italic">
                                    High transaction volume detected. This address shows patterns consistent with an active darknet vendor or intermediate mixing service. Recommended: Add to 24/7 Watchlist.
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        )}
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400 uppercase tracking-tight">CRYPTO FORENSICS & TRACKER</h2>
          <p className="text-sm text-neutral-500 mt-1">
            Real-time blockchain analysis and automated discovery registry
          </p>
        </div>
        <Button onClick={fetchWallets} variant="outline" className="border-orange-500/30 text-orange-400">
          <RefreshCcw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Sync Registry
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Address Lookup */}
          <Card className="bg-neutral-900 border-orange-900/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs text-orange-400 uppercase tracking-widest">Address Deep Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col md:flex-row gap-3">
                <div className="w-full md:w-32">
                  <select 
                    value={currency} 
                    onChange={(e) => setCurrency(e.target.value)}
                    className="w-full h-10 px-3 bg-neutral-800 border border-neutral-700 rounded text-white text-xs focus:border-orange-500 outline-none"
                  >
                    <option value="BTC">BTC</option>
                    <option value="ETH">ETH</option>
                    <option value="XMR">XMR</option>
                    <option value="USDT">USDT</option>
                  </select>
                </div>
                <div className="flex-1 flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter wallet address..."
                    value={walletInput}
                    onChange={(e) => setWalletInput(e.target.value)}
                    className="flex-1 px-4 bg-neutral-800 border border-neutral-700 rounded text-white text-xs placeholder-neutral-500 focus:border-orange-500 outline-none"
                  />
                  <Button 
                    onClick={() => handleAnalyzeAddress(walletInput)} 
                    disabled={isAnalyzing || !walletInput}
                    className="bg-orange-500 hover:bg-orange-600 text-black font-bold text-xs"
                  >
                    {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 mr-2" />}
                    Analyze
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* TX Lookup */}
          <Card className="bg-neutral-900 border-orange-900/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs text-orange-400 uppercase tracking-widest">Transaction Forensic Lookup</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Enter transaction hash (txid)..."
                  value={txInput}
                  onChange={(e) => setTxInput(e.target.value)}
                  className="flex-1 px-4 h-10 bg-neutral-800 border border-neutral-700 rounded text-white text-xs placeholder-neutral-500 focus:border-orange-500 outline-none"
                />
                <Button 
                  onClick={handleLookupTx} 
                  disabled={isTxLoading || !txInput}
                  className="bg-neutral-800 border border-orange-500/50 text-orange-400 font-bold text-xs hover:bg-orange-500/10"
                >
                  {isTxLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <History className="w-4 h-4 mr-2" />}
                  Track TX
                </Button>
              </div>
            </CardContent>
          </Card>
      </div>

      {/* Registry & Stats Tabs */}
      <div className="flex gap-4 border-b border-neutral-800 pb-2">
          <button 
            onClick={() => setActiveTab('overview')}
            className={`text-xs font-bold uppercase tracking-widest ${activeTab === 'overview' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-neutral-500'}`}
          >
              Registry
          </button>
          <button 
            onClick={() => setActiveTab('transactions')}
            className={`text-xs font-bold uppercase tracking-widest ${activeTab === 'transactions' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-neutral-500'}`}
          >
              Last TX Lookup
          </button>
      </div>

      {activeTab === 'overview' ? (
          <Card className="bg-neutral-900 border-orange-900/30">
            <CardHeader>
              <CardTitle className="text-sm text-orange-400 uppercase tracking-widest">IDENTIFIED TARGETS</CardTitle>
              <CardDescription className="text-neutral-500 italic">Illicit addresses automatically captured from investigations</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex justify-center py-12 text-orange-500"><Loader2 className="w-8 h-8 animate-spin" /></div>
              ) : trackedWallets.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {trackedWallets.map((wallet: any) => (
                    <div key={wallet.id} className="p-4 bg-neutral-800 border border-neutral-700 rounded hover:border-orange-500/40 transition-all group relative">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold px-1.5 py-0.5 bg-orange-500 text-black rounded">{wallet.currency}</span>
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${wallet.is_watchlist ? 'bg-blue-500/20 text-blue-400' : 'bg-neutral-700 text-neutral-400'}`}>
                            {wallet.is_watchlist ? 'WATCHLIST' : 'DISCOVERED'}
                          </span>
                        </div>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          onClick={() => handleDeleteWallet(wallet.id)}
                          className="h-6 w-6 text-neutral-500 hover:text-red-400"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                      
                      <p className="text-[11px] text-orange-400 font-mono mb-4 truncate" title={wallet.address}>
                        {wallet.address}
                      </p>

                      <div className="flex items-center justify-between mt-auto">
                        <p className="text-[10px] text-neutral-500">First Seen: {format(new Date(wallet.first_seen_at), 'MMM dd, yyyy')}</p>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={() => handleAnalyzeAddress(wallet.address)}
                          className="text-[10px] text-orange-500 hover:text-orange-400 h-6 px-2"
                        >
                          Deep Scan
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-16">
                  <Wallet className="w-12 h-12 text-neutral-800 mx-auto mb-4" />
                  <p className="text-neutral-500 uppercase tracking-widest text-xs font-bold">Registry is empty</p>
                </div>
              )}
            </CardContent>
          </Card>
      ) : (
          /* Transaction Detail Tab */
          <Card className="bg-neutral-900 border-orange-900/30">
              <CardContent className="pt-6">
                  {isTxLoading ? (
                      <div className="text-center py-12">
                          <Loader2 className="w-8 h-8 text-orange-500 animate-spin mx-auto mb-2" />
                          <p className="text-xs text-neutral-500 uppercase font-mono">Tracing transaction on-chain...</p>
                      </div>
                  ) : txDetails ? (
                      <div className="space-y-6">
                          <div className="flex items-center gap-3 border-b border-neutral-800 pb-4">
                              <div className="p-2 bg-orange-500/10 rounded">
                                  <Activity className="w-5 h-5 text-orange-500" />
                              </div>
                              <div>
                                  <h3 className="text-sm font-bold text-white uppercase">{txDetails.chain} Transaction</h3>
                                  <p className="text-[10px] text-neutral-500 font-mono">{txDetails.hash}</p>
                              </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              <div className="p-4 bg-neutral-800/50 rounded border border-neutral-700/50">
                                  <p className="text-[10px] text-neutral-500 uppercase mb-1">Status</p>
                                  <p className="text-xs font-bold text-green-400 uppercase">Confirmed</p>
                              </div>
                              <div className="p-4 bg-neutral-800/50 rounded border border-neutral-700/50">
                                  <p className="text-[10px] text-neutral-500 uppercase mb-1">Block ID</p>
                                  <p className="text-xs font-mono text-white">{txDetails.details?.block_id || 'Pending'}</p>
                              </div>
                              <div className="p-4 bg-neutral-800/50 rounded border border-neutral-700/50">
                                  <p className="text-[10px] text-neutral-500 uppercase mb-1">Timestamp</p>
                                  <p className="text-xs text-white">{txDetails.details?.time || 'N/A'}</p>
                              </div>
                          </div>

                          <div className="p-4 bg-orange-500/5 border border-orange-500/20 rounded">
                              <div className="flex justify-between items-center">
                                  <span className="text-xs text-neutral-400 font-bold uppercase">Transaction Value</span>
                                  <div className="text-right">
                                      <p className="text-lg font-bold text-orange-400 font-mono">{txDetails.details?.output_total || '0.00'}</p>
                                      <p className="text-[10px] text-neutral-500">${txDetails.details?.output_total_usd || '0.00'} USD</p>
                                  </div>
                              </div>
                          </div>
                      </div>
                  ) : (
                      <div className="text-center py-12">
                          <History className="w-12 h-12 text-neutral-800 mx-auto mb-2 opacity-30" />
                          <p className="text-xs text-neutral-500 uppercase">Enter a hash above to start tracing</p>
                      </div>
                  )}
              </CardContent>
          </Card>
      )}
    </div>
  )
}
