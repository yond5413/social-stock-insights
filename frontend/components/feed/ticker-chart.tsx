"use client"

import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts"

const data = [
  { value: 100 },
  { value: 104 },
  { value: 102 },
  { value: 108 },
  { value: 106 },
  { value: 110 },
  { value: 112 },
]

export function TickerChart({ ticker, trend = "up" }: { ticker: string, trend?: "up" | "down" }) {
  const color = trend === "up" ? "#16a34a" : "#dc2626" // green-600 : red-600

  return (
    <div className="h-[40px] w-[100px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
           <defs>
            <linearGradient id={`gradient-${ticker}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={color} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            fill={`url(#gradient-${ticker})`}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}



