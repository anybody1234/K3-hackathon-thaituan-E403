import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('codebase'))
from storage.database import Database

async def test():
    db = Database()
    await db.connect()
    
    user_id = '758326652719333426'
    reactions = await db.get_user_reactions(user_id)
    print(f'Total reactions for user {user_id}: {len(reactions)}')
    for r in reactions:
        print(f'Post: {r["post_id"]}, Type: {type(r["post_id"])}, Reaction: {r["reaction_type"]}')
        
    await db.close()

asyncio.run(test())
