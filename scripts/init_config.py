"""Create independent credentials; never edit or copy the source database config."""
import argparse
import secrets
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-env', type=Path, help='Read only these existing model credentials')
    args = p.parse_args()
    target = ROOT / '.env'
    if target.exists():
        print('.env already exists; preserving credentials')
        return
    values = dict(dotenv_values(ROOT / '.env.example'))
    for name in ('DB_PASSWORD', 'REDIS_PASSWORD', 'JWT_SECRET'):
        values[name] = secrets.token_urlsafe(32)
    # The upstream login UI accepts at most 32 characters.
    values['ADMIN_PASSWORD'] = 'Aa1!' + secrets.token_urlsafe(18)
    values['SYSTEM_AES_KEY'] = secrets.token_hex(16)
    if args.model_env:
        source = dotenv_values(args.model_env)
        for key in ('NVIDIA_API_KEY', 'NVIDIA_API_URL', 'MINIMAX_API_KEY', 'MINIMAX_API_URL', 'MINIMAX_MODEL'):
            if source.get(key):
                values[key] = source[key]
    def quote(value):
        return "'" + str(value or '').replace('\\', '\\\\').replace("'", "\\'") + "'"
    with target.open('x', encoding='utf-8') as f:
        f.write('\n'.join(k+'='+quote(v) for k,v in values.items())+'\n')
    print('Created independent .env; credentials are not printed')
    print('Model credentials present:', {k: bool(values.get(k)) for k in ('NVIDIA_API_KEY','MINIMAX_API_KEY')})

if __name__ == '__main__':
    main()
