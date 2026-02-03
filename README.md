# Gold-Silver-Intelligence Agent

Hệ thống Multi-Agent tự động thu thập tin tức, phân tích tác động giá Vàng/Bạc và gửi cảnh báo qua Telegram.

## Tính năng

- **NewsHunter Agent**: Tự động tìm kiếm tin tức Vàng/Bạc trong 24h gần nhất
- **MarketAnalyst Agent**: Phân tích xu hướng Bullish/Bearish dựa trên tin tức
- **Telegram Integration**: Gửi báo cáo phân tích trực tiếp qua Telegram

## Cài đặt

```bash
# Clone repo
git clone https://github.com/your-username/gold-silver-intelligence.git
cd gold-silver-intelligence

# Tạo môi trường ảo
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Cài đặt dependencies
pip install -r requirements.txt

# Cấu hình môi trường
cp .env.example .env
# Điền API keys vào file .env
```

## Sử dụng

```bash
python src/main.py
```

## Cấu trúc

```
gold-silver-intelligence/
├── libs/antigravity-kit/  # Utility library
├── src/
│   ├── config.py          # Environment config
│   ├── agents.py          # AgentScope agents
│   ├── telegram_bot.py    # Telegram integration
│   └── main.py            # Main pipeline
├── .env.example
└── requirements.txt
```

## Framework

- [AgentScope](https://github.com/modelscope/agentscope) - Multi-agent orchestration
- [Serper API](https://serper.dev/) - Google Search API

## License

MIT
