import type { MarketData } from '../lib/api'
import { TrendingUp } from 'lucide-react'

interface MarketCardProps {
  data: MarketData
}

export default function MarketCard({ data }: MarketCardProps) {
  const top = data.records.slice(0, 5)

  return (
    <div className="flex justify-center my-2">
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-4 w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <div className="bg-green-600 p-2 rounded-lg">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-800">Market Price</h3>
            <p className="text-xs text-gray-500">
              {data.crop} · {data.state}
            </p>
          </div>
        </div>

        {top.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-2">No records available</p>
        ) : (
          <div className="space-y-2">
            {/* Column headers */}
            <div className="grid grid-cols-3 text-xs font-medium text-gray-400 uppercase px-1">
              <span>Market</span>
              <span className="text-center">Price (₹/qtl)</span>
              <span className="text-right">Date</span>
            </div>

            {top.map((r, i) => (
              <div
                key={i}
                className="grid grid-cols-3 items-center bg-white rounded-lg px-3 py-2 text-sm shadow-sm"
              >
                <span className="text-gray-700 truncate">{r.market}</span>
                <span className="text-center font-bold text-green-700">
                  ₹{r.price.toLocaleString('en-IN')}
                </span>
                <span className="text-right text-gray-400 text-xs">{r.date}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}