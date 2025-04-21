import os
import logging
from typing import List, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP
from r2r import R2RClient

mcp = FastMCP("R2R Search Tool")

r2r_client = None


def init_r2r_client():
    global r2r_client
    if r2r_client is None:
        r2r_base_url = os.getenv("R2R_BASE_URL", "http://localhost:7272")
        r2r_client = R2RClient(r2r_base_url)
        
        r2r_username = os.getenv("R2R_USERNAME")
        r2r_password = os.getenv("R2R_PASSWORD")

        logging.info(f"R2R base URL: {r2r_base_url}, Username: {r2r_username}")
        if r2r_username and r2r_password:
            try:
                r2r_client.users.login(r2r_username, r2r_password)
                logging.info("R2R login successful")
            except Exception as e:
                logging.error(f"R2R login failed: {e}")




def verify_jwt_expiration(token_str: str) -> bool:
    if not token_str:
        return False
        
    try:
        import jwt
        from datetime import datetime
        
        decoded_token = jwt.decode(token_str, options={"verify_signature": False, "verify_exp": False})
        
        exp_time = decoded_token.get('exp')
        if not exp_time:
            return False
            
        expiration_time = datetime.fromtimestamp(exp_time)
        current_time = datetime.now()
        
        return current_time < expiration_time
    except Exception as e:
        logging.error(f"Token verification error: {e}")
        return False


def check_login():
    global r2r_client
    if not r2r_client:
        init_r2r_client()
        return
        
    r2r_username = os.getenv("R2R_USERNAME")
    r2r_password = os.getenv("R2R_PASSWORD")
    if not (r2r_username and r2r_password):
        return
        
    try:
        if hasattr(r2r_client, 'access_token') and r2r_client.access_token:
            if verify_jwt_expiration(r2r_client.access_token):
                return
                
        if hasattr(r2r_client, '_refresh_token') and r2r_client._refresh_token:
            if verify_jwt_expiration(r2r_client._refresh_token):
                try:
                    r2r_client.refresh_access_token()
                    return
                except:
                    pass

        r2r_client.users.login(r2r_username, r2r_password)
        logging.info("R2R re-login successful")
    except Exception as e:
        logging.error(f"R2R login check failed: {e}")


@mcp.tool()
def search_chunks(query: str, file_ids: Optional[List[str]] = None, limit: int = 5) -> Dict[str, Any]:
    """
    Search document chunks in R2R system
    
    Args:
        query: Search query
        file_ids: List of file IDs to filter search scope
        limit: Maximum number of results to return
        
    Returns:
        Search results
    """
    check_login()
    
    filters = {}
    if file_ids:
        filters = {"document_id": {"$in": file_ids}}
    
    try:
        search_response = r2r_client.chunks.search(
            query=query,
            search_settings={
                "use_hybrid_search": True,
                "filters": filters,
                "search_limit": limit,
            },
        )
        results = search_response.model_dump().get('results', [])
        
        processed_results = []
        for result in results:
            document_id = str(result.get("document_id", ""))
            chunk_id = str(result.get("id", ""))
            
            try:
                response = r2r_client.chunks.retrieve(id=chunk_id)
                text = response.model_dump().get('results', {}).get("text", "")
                
                processed_results.append({
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "text": text,
                    "score": result.get("metadata", {}).get("search_score", 0) if isinstance(result.get("metadata"), dict) else 0
                })

                logging.info(f"Retrieved chunk {chunk_id} from document {document_id}, text: {text}")

            except Exception as e:
                logging.error(f"Error retrieving chunk {chunk_id}: {e}")
                continue
        
        return {
            "query": query,
            "results": processed_results,
            "total": len(processed_results)
        }
        
    except Exception as e:
        logging.error(f"R2R search error: {e}")
        return {
            "query": query,
            "results": [],
            "total": 0,
            "error": str(e)
        }


if __name__ == "__main__":
    init_r2r_client()
    
    mcp.run()