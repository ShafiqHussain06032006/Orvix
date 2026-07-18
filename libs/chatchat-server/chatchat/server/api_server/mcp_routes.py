from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from chatchat.server.api_server.api_schemas import (
    MCPConnectionCreate,
    MCPConnectionUpdate,
    MCPConnectionResponse,
    MCPConnectionListResponse,
    MCPConnectionSearchRequest,
    MCPConnectionStatusResponse,
    MCPProfileCreate,
    MCPProfileResponse,
    MCPProfileStatusResponse,
)
from chatchat.server.db.repository.mcp_connection_repository import (
    add_mcp_connection,
    update_mcp_connection,
    get_mcp_connection_by_id,
    get_mcp_connections_by_server_name,
    get_all_mcp_connections,
    get_enabled_mcp_connections,
    delete_mcp_connection,
    enable_mcp_connection,
    disable_mcp_connection,
    search_mcp_connections,
    get_mcp_profile,
    create_mcp_profile,
    update_mcp_profile,
    reset_mcp_profile,
    delete_mcp_profile,
)
from chatchat.utils import build_logger


logger = build_logger()
mcp_router = APIRouter(prefix="/api/v1/mcp_connections", tags=["MCP Connections"])


# MCP Profile related routes - put them in front to avoid confusion with {connection_id} conflict
@mcp_router.get("/profile", response_model=MCPProfileResponse, summary="Get MCP common configuration")
async def get_mcp_profile_endpoint():
    """
    Get MCP common configuration
    """
    logger.info("Get MCP common configuration")
    try:
        profile = get_mcp_profile()
        if profile:
            logger.info("Successfully obtained MCP common configuration")
            return MCPProfileResponse(
                timeout=profile["timeout"],
                working_dir=profile["working_dir"],
                env_vars=profile["env_vars"],
                update_time=profile["update_time"]
            )
        else:
            logger.info("MCP general configuration does not exist, return to default configuration")
            # If no configuration exists, return to the default configuration
            return MCPProfileResponse(
                timeout=30,
                working_dir="/tmp",
                env_vars={
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                    "PYTHONPATH": "/app",
                    "HOME": "/tmp"
                },
                update_time=datetime.now().isoformat()
            )
    
    except Exception as e:
        logger.error(f"Failed to obtain MCP common configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/profile", response_model=MCPProfileResponse, summary="Create/update MCP common configuration")
async def create_or_update_mcp_profile(profile_data: MCPProfileCreate):
    """
    Create or update MCP common configuration
    """
    logger.info(f"Create/update MCP common configuration: timeout={profile_data.timeout}, working_dir={profile_data.working_dir}")
    try:
        profile_id = create_mcp_profile(
            timeout=profile_data.timeout,
            working_dir=profile_data.working_dir,
            env_vars=profile_data.env_vars,
        )
        
        profile = get_mcp_profile()
        logger.info(f"Successfully created/updated MCP common configuration, ID: {profile_id}")
        return MCPProfileResponse(
            timeout=profile["timeout"],
            working_dir=profile["working_dir"],
            env_vars=profile["env_vars"],
            update_time=profile["update_time"]
        )
    
    except Exception as e:
        logger.error(f"Failed to create/update MCP common configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.put("/profile", response_model=MCPProfileResponse, summary="Update MCP common configuration")
async def update_mcp_profile_endpoint(profile_data: MCPProfileCreate):
    """
    Update MCP common configuration
    """
    logger.info(f"Update MCP common configuration: timeout={profile_data.timeout}, working_dir={profile_data.working_dir}")
    try:
        profile_id = update_mcp_profile(
            timeout=profile_data.timeout,
            working_dir=profile_data.working_dir,
            env_vars=profile_data.env_vars,
        )
        
        profile = get_mcp_profile()
        logger.info(f"Successfully updated MCP common configuration, ID: {profile_id}")
        return MCPProfileResponse(
            timeout=profile["timeout"],
            working_dir=profile["working_dir"],
            env_vars=profile["env_vars"],
            update_time=profile["update_time"]
        )
    
    except Exception as e:
        logger.error(f"Failed to update MCP common configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/profile/reset", response_model=MCPProfileStatusResponse, summary="Reset MCP common configuration")
async def reset_mcp_profile_endpoint():
    """
    Reset MCP common configuration to default
    """
    logger.info("Reset MCP common configuration to default")
    try:
        success = reset_mcp_profile()
        if success:
            logger.info("Successfully reset MCP common configuration")
            return MCPProfileStatusResponse(
                success=True,
                message="MCP common configuration reset to defaults"
            )
        else:
            logger.error("Reset MCP common configuration failed")
            return MCPProfileStatusResponse(
                success=False,
                message="Reset MCP common configuration failed"
            )
    
    except Exception as e:
        logger.error(f"Resetting MCP common configuration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.delete("/profile", response_model=MCPProfileStatusResponse, summary="Delete MCP common configuration")
async def delete_mcp_profile_endpoint():
    """
    Delete MCP common configuration
    """
    logger.info("Delete MCP common configuration")
    try:
        success = delete_mcp_profile()
        if success:
            logger.info("Successfully deleted MCP common configuration")
            return MCPProfileStatusResponse(
                success=True,
                message="MCP common configuration removed"
            )
        else:
            logger.error("Deletion of MCP common configuration failed")
            return MCPProfileStatusResponse(
                success=False,
                message="Deletion of MCP common configuration failed"
            )
    
    except Exception as e:
        logger.error(f"Deletion of MCP common configuration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def model_to_response(model) -> MCPConnectionResponse:
    """Convert database model to response object"""
    return MCPConnectionResponse(
        id=model.id,
        server_name=model.server_name,
        args=model.args,
        env=model.env,
        cwd=model.cwd,
        transport=model.transport,
        timeout=model.timeout,
        enabled=model.enabled,
        description=model.description,
        config=model.config,
        create_time=model.create_time.isoformat() if model.create_time else None,
        update_time=model.update_time.isoformat() if model.update_time else None,
    )


@mcp_router.post("/", response_model=MCPConnectionResponse, summary="Create MCP connection")
async def create_mcp_connection(connection_data: MCPConnectionCreate):
    """
    Create a new MCP connection configuration
    """
    logger.info(f"Create MCP connection: {connection_data.server_name}")
    try:
        # Check if the server name already exists
        existing = get_mcp_connections_by_server_name(server_name=connection_data.server_name)
        if existing:
            logger.error(f"Server name '{connection_data.server_name}' Already exists")
            raise HTTPException(
                status_code=400,
                detail=f"Server name '{connection_data.server_name}' Already exists"
            )
        
        connection_id = add_mcp_connection(
            server_name=connection_data.server_name,
            args=connection_data.args,
            env=connection_data.env,
            cwd=connection_data.cwd,
            transport=connection_data.transport,
            timeout=connection_data.timeout,
            enabled=connection_data.enabled,
            description=connection_data.description,
            config=connection_data.config,
        )
        
        connection = get_mcp_connection_by_id(connection_id)
        logger.info(f"MCP connection successfully created: {connection_data.server_name}, ID: {connection_id}")
        return MCPConnectionResponse(
            id=connection["id"],
            server_name=connection["server_name"],
            args=connection["args"],
            env=connection["env"],
            cwd=connection["cwd"],
            transport=connection["transport"],
            timeout=connection["timeout"],
            enabled=connection["enabled"],
            description=connection["description"],
            config=connection["config"],
            create_time=connection["create_time"],
            update_time=connection["update_time"],
        )
    
    except Exception as e:
        logger.error(f"Failed to create MCP connection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/", response_model=MCPConnectionListResponse, summary="Get MCP connection list")
async def list_mcp_connections(
    enabled_only: bool = Query(False, description="Return only enabled connections")
):
    """
    Get a list of all MCP connection configurations
    """
    logger.info(f"Get MCP connection list, enabled_only={enabled_only}")
    try:
        if enabled_only:
            connections = get_enabled_mcp_connections()
        else:
            connections = get_all_mcp_connections()
        
        response_connections = [MCPConnectionResponse(
            id=conn["id"],
            server_name=conn["server_name"],
            args=conn["args"],
            env=conn["env"],
            cwd=conn["cwd"],
            transport=conn["transport"],
            timeout=conn["timeout"],
            enabled=conn["enabled"],
            description=conn["description"],
            config=conn["config"],
            create_time=conn["create_time"],
            update_time=conn["update_time"],
        ) for conn in connections]
        logger.info(f"Successfully obtained MCP connection list, total {len(response_connections)} connections")
        return MCPConnectionListResponse(
            connections=response_connections,
            total=len(response_connections)
        )
    
    except Exception as e:
        logger.error(f"Failed to get MCP connection list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/{connection_id}", response_model=MCPConnectionResponse, summary="Get MCP connection details")
async def get_mcp_connection(connection_id: str):
    """
    Get MCP connection configuration details based on ID
    """
    logger.info(f"Get MCP connection details: {connection_id}")
    try:
        connection = get_mcp_connection_by_id(connection_id)
        if not connection:
            logger.error(f"Connection ID '{connection_id}' does not exist")
            raise HTTPException(
                status_code=404,
                detail=f"Connection ID '{connection_id}' does not exist"
            )
        
        logger.info(f"Successfully obtained MCP connection details: {connection_id}")
        return model_to_response(connection)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MCP connection details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.put("/{connection_id}", response_model=MCPConnectionStatusResponse, summary="Update MCP connection")
async def update_mcp_connection_by_id(
    connection_id: str, 
    update_data: MCPConnectionUpdate
):
    """
    Update MCP connection configuration
    """
    logger.info(f"Update MCP connection: {connection_id}")
    try:
        # Check if the connection exists
        existing = get_mcp_connection_by_id(connection_id)
        if not existing:
            logger.error(f"Connection ID '{connection_id}' does not exist")
         
            return MCPConnectionStatusResponse(
                    connection_id=connection_id,
                    success=False,
                    message=f"Connection ID '{connection_id}' does not exist"
            )   
        
        
        # If updating the name, check if it conflicts with other connections
        if update_data.server_name and update_data.server_name != existing.server_name:
            name_existing = get_connections_by_server_name(server_name=update_data.server_name)
            if name_existing:
                logger.error(f"Server name '{update_data.server_name}' Already exists")
                return MCPConnectionStatusResponse(
                    connection_id=connection_id,
                    success=False,
                    message=f"Server name '{update_data.server_name}' Already exists"
                )   
        
        updated_id = update_mcp_connection(
            connection_id=connection_id,
            server_name=update_data.server_name,
            args=update_data.args,
            env=update_data.env,
            cwd=update_data.cwd,
            transport=update_data.transport,
            timeout=update_data.timeout,
            enabled=update_data.enabled,
            description=update_data.description,
            config=update_data.config,
        )
        
        if updated_id:
            connection = get_mcp_connection_by_id(connection_id)
            logger.info(f"Successfully updated MCP connection: {connection_id}")
            return MCPConnectionStatusResponse(
                connection_id=connection["id"],
                success=True,
                message="successfully updated",
            )
        else:
            logger.error("Update MCP connection failed")
            return MCPConnectionStatusResponse(
                connection_id=connection_id,
                success=False,
                message=f"Update MCP connection failed",
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update MCP connection failed: {str(e)}")
        return MCPConnectionStatusResponse(
                connection_id=connection_id,
                success=False,
                message=f"Update MCP connection failed: {str(e)}",
        )


@mcp_router.delete("/{connection_id}", response_model=MCPConnectionStatusResponse, summary="Delete MCP connection")
async def delete_mcp_connection_by_id(connection_id: str):
    """
    Delete MCP connection configuration
    """
    logger.info(f"Delete MCP connection: {connection_id}")
    try:
        # Check if the connection exists
        existing = get_mcp_connection_by_id(connection_id)
        if not existing:
            logger.error(f"Connection ID '{connection_id}' does not exist")
            raise HTTPException(
                status_code=404,
                detail=f"Connection ID '{connection_id}' does not exist"
            )
        
        success = delete_mcp_connection(connection_id)
        if success:
            logger.info(f"Successfully deleted MCP connection: {connection_id}")
            return MCPConnectionStatusResponse(
                success=True,
                message="Connection deleted successfully",
                connection_id=connection_id
            )
        else:
            logger.error(f"Removing MCP connection failed: {connection_id}")
            return MCPConnectionStatusResponse(
                success=False,
                message="Connection deletion failed",
                connection_id=connection_id
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Removing MCP connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/{connection_id}/enable", response_model=MCPConnectionStatusResponse, summary="Enable MCP connection")
async def enable_mcp_connection_endpoint(connection_id: str):
    """
    Enables the specified MCP connection
    """
    logger.info(f"Enable MCP connection: {connection_id}")
    try:
        # Check if the connection exists
        existing = get_mcp_connection_by_id(connection_id)
        if not existing:
            logger.error(f"Connection ID '{connection_id}' does not exist")
            raise HTTPException(
                status_code=404,
                detail=f"Connection ID '{connection_id}' does not exist"
            )
        
        success = enable_mcp_connection(connection_id)
        if success:
            logger.info(f"Successfully enabled MCP connection: {connection_id}")
            return MCPConnectionStatusResponse(
                success=True,
                message="Connection enabled successfully",
                connection_id=connection_id
            )
        else:
            logger.error(f"Failed to enable MCP connection: {connection_id}")
            return MCPConnectionStatusResponse(
                success=False,
                message="Connection enablement failed",
                connection_id=connection_id
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable MCP connection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/{connection_id}/disable", response_model=MCPConnectionStatusResponse, summary="Disable MCP connections")
async def disable_mcp_connection_endpoint(connection_id: str):
    """
    Disable specified MCP connection
    """
    logger.info(f"Disable MCP connections: {connection_id}")
    try:
        # Check if the connection exists
        existing = get_mcp_connection_by_id(connection_id)
        if not existing:
            logger.error(f"Connection ID '{connection_id}' does not exist")
            raise HTTPException(
                status_code=404,
                detail=f"Connection ID '{connection_id}' does not exist"
            )
        
        success = disable_mcp_connection(connection_id)
        if success:
            logger.info(f"Successfully disabled MCP connection: {connection_id}")
            return MCPConnectionStatusResponse(
                success=True,
                message="Connection disabled successfully",
                connection_id=connection_id
            )
        else:
            logger.error(f"Disable MCP connection failed: {connection_id}")
            return MCPConnectionStatusResponse(
                success=False,
                message="Connection disable failed",
                connection_id=connection_id
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Disable MCP connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




@mcp_router.post("/search", response_model=MCPConnectionListResponse, summary="Search for MCP connections")
async def search_mcp_connections_endpoint(search_request: MCPConnectionSearchRequest):
    """
    Search MCP connection configurations based on criteria
    """
    logger.info(f"Search for MCP connections: keyword={search_request.keyword}, transport={search_request.transport}, enabled={search_request.enabled}, limit={search_request.limit}")
    try:
        connections = search_mcp_connections(
            keyword=search_request.keyword,
            transport=search_request.transport,
            enabled=search_request.enabled,
            limit=search_request.limit,
        )
        
        response_connections = [MCPConnectionResponse(
            id=conn["id"],
            server_name=conn["server_name"],
            args=conn["args"],
            env=conn["env"],
            cwd=conn["cwd"],
            transport=conn["transport"],
            timeout=conn["timeout"],
            enabled=conn["enabled"],
            description=conn["description"],
            config=conn["config"],
            create_time=conn["create_time"],
            update_time=conn["update_time"],
        ) for conn in connections]
        logger.info(f"Successfully searched for MCP connection, found {len(response_connections)} connections")
        return MCPConnectionListResponse(
            connections=response_connections,
            total=len(response_connections)
        )
    
    except Exception as e:
        logger.error(f"Search MCP connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/server/{server_name}", response_model=MCPConnectionListResponse, summary="Get connection based on server name")
async def get_connections_by_server_name(server_name: str):
    """
    Get MCP connection configuration list based on server name
    """
    logger.info(f"Get MCP connection based on server name: {server_name}")
    try:
        connections = get_mcp_connections_by_server_name(server_name)
        
        response_connections = [MCPConnectionResponse(
            id=conn["id"],
            server_name=conn["server_name"],
            args=conn["args"],
            env=conn["env"],
            cwd=conn["cwd"],
            transport=conn["transport"],
            timeout=conn["timeout"],
            enabled=conn["enabled"],
            description=conn["description"],
            config=conn["config"],
            create_time=conn["create_time"],
            update_time=conn["update_time"],
        ) for conn in connections]
        logger.info(f"Successfully obtained MCP connection based on server name, found {len(response_connections)} connections")
        return MCPConnectionListResponse(
            connections=response_connections,
            total=len(response_connections)
        )
    
    except Exception as e:
        logger.error(f"Failed to get MCP connection based on server name: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/enabled/list", response_model=MCPConnectionListResponse, summary="Get enabled MCP connections")
async def list_enabled_mcp_connections():
    """
    Get all enabled MCP connection configurations
    """
    logger.info("Get the list of enabled MCP connections")
    try:
        connections = get_enabled_mcp_connections()
        
        response_connections = [MCPConnectionResponse(
            id=conn["id"],
            server_name=conn["server_name"],
            args=conn["args"],
            env=conn["env"],
            cwd=conn["cwd"],
            transport=conn["transport"],
            timeout=conn["timeout"],
            enabled=conn["enabled"],
            description=conn["description"],
            config=conn["config"],
            create_time=conn["create_time"],
            update_time=conn["update_time"],
        ) for conn in connections]
        logger.info(f"Successfully obtained the list of enabled MCP connections, total {len(response_connections)} connections")
        return MCPConnectionListResponse(
            connections=response_connections,
            total=len(response_connections)
        )
    
    except Exception as e:
        logger.error(f"Failed to get list of enabled MCP connections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




# MCP Profile related routes have been moved to the beginning of the file to avoid routing conflicts