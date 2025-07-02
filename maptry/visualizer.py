"""
Visualizer module for creating interactive maps of optimized routes.
Uses Folium to generate HTML maps with truck routes and delivery points.
"""

import os
from typing import List, Dict, Optional, Tuple
import folium
from folium import plugins
import json
import random

from data_loader import Truck, DeliveryPoint
from optimizer import OptimizedRoute
from eta_calculator import ETAInfo
from router import Router


class RouteVisualizer:
    """Creates interactive visualizations of truck routes and delivery points."""
    
    def __init__(self, router: Optional[Router] = None):
        """
        Initialize visualizer.
        
        Args:
            router: Router instance for getting route geometries
        """
        self.router = router
        self.colors = [
            '#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#00FFFF', 
            '#FFA500', '#800080', '#FFC0CB', '#A52A2A', '#808080'
        ]
    
    def create_route_map(self,
                        trucks: List[Truck],
                        delivery_points: List[DeliveryPoint],
                        optimized_routes: List[OptimizedRoute],
                        etas: Optional[Dict[str, List[ETAInfo]]] = None,
                        center: Optional[List[float]] = None,
                        zoom_start: int = 12) -> folium.Map:
        """
        Create an interactive map showing optimized routes.
        
        Args:
            trucks: List of truck objects
            delivery_points: List of delivery point objects
            optimized_routes: List of optimized routes
            etas: Optional ETA information for each route
            center: Map center coordinates [lat, lon]
            zoom_start: Initial zoom level
            
        Returns:
            Folium map object
        """
        # Determine map center if not provided
        if center is None:
            center = self._calculate_map_center(trucks, delivery_points)
        
        # Create base map
        m = folium.Map(
            location=center,
            zoom_start=zoom_start,
            tiles='OpenStreetMap'
        )
        
        # Add truck starting positions
        self._add_truck_markers(m, trucks)
        
        # Add delivery points
        self._add_delivery_markers(m, delivery_points, etas)
        
        # Add routes
        self._add_route_lines(m, trucks, delivery_points, optimized_routes)
        
        # Add legend
        self._add_legend(m, optimized_routes)
        
        # Add map controls
        folium.LayerControl().add_to(m)
        plugins.Fullscreen().add_to(m)
        
        return m
    
    def _calculate_map_center(self, trucks: List[Truck], 
                            delivery_points: List[DeliveryPoint]) -> List[float]:
        """Calculate the center point for the map."""
        all_coords = []
        
        # Add truck positions
        for truck in trucks:
            all_coords.append(truck.start)
        
        # Add delivery points
        for point in delivery_points:
            all_coords.append(point.location)
        
        if not all_coords:
            return [0, 0]
        
        # Calculate center
        avg_lat = sum(coord[0] for coord in all_coords) / len(all_coords)
        avg_lon = sum(coord[1] for coord in all_coords) / len(all_coords)
        
        return [avg_lat, avg_lon]
    
    def _add_truck_markers(self, m: folium.Map, trucks: List[Truck]) -> None:
        """Add truck starting position markers to the map."""
        for i, truck in enumerate(trucks):
            color = self.colors[i % len(self.colors)]
            
            # Create truck marker
            folium.Marker(
                location=truck.start,
                popup=folium.Popup(
                    f"""
                    <b>Truck {truck.id}</b><br>
                    Capacity: {truck.capacity}<br>
                    Speed: {truck.speed_kmh} km/h<br>
                    Location: {truck.start[0]:.4f}, {truck.start[1]:.4f}
                    """,
                    max_width=200
                ),
                tooltip=f"Truck {truck.id}",
                icon=folium.Icon(color='red', icon='truck', prefix='fa')
            ).add_to(m)
            
            # Add circle around truck
            folium.Circle(
                location=truck.start,
                radius=500,  # 500 meters
                color=color,
                weight=2,
                fill=True,
                fillColor=color,
                fillOpacity=0.1
            ).add_to(m)
    
    def _add_delivery_markers(self, m: folium.Map, 
                            delivery_points: List[DeliveryPoint],
                            etas: Optional[Dict[str, List[ETAInfo]]] = None) -> None:
        """Add delivery point markers to the map."""
        # Create ETA lookup for quick access
        eta_lookup = {}
        if etas:
            for truck_id, truck_etas in etas.items():
                for eta in truck_etas:
                    eta_lookup[eta.point_id] = eta
        
        for point in delivery_points:
            eta_info = eta_lookup.get(point.id)
            
            # Create popup content
            popup_content = f"""
            <b>Delivery Point {point.id}</b><br>
            Location: {point.location[0]:.4f}, {point.location[1]:.4f}<br>
            Demand: {point.demand}<br>
            Time Window: {point.time_window_start} - {point.time_window_end}<br>
            Priority: {point.priority}
            """
            
            if eta_info:
                popup_content += f"""<br>
                <b>ETA:</b> {eta_info.eta}<br>
                <b>Travel Time:</b> {eta_info.travel_time_minutes:.1f} min<br>
                <b>Distance:</b> {eta_info.distance_from_previous_m:.0f} m
                """
            
            # Determine marker color based on priority
            if point.priority >= 3:
                marker_color = 'red'
            elif point.priority >= 2:
                marker_color = 'orange'
            else:
                marker_color = 'green'
            
            folium.Marker(
                location=point.location,
                popup=folium.Popup(popup_content, max_width=250),
                tooltip=f"Point {point.id} (Priority: {point.priority})",
                icon=folium.Icon(color=marker_color, icon='package', prefix='fa')
            ).add_to(m)
    
    def _add_route_lines(self, m: folium.Map,
                        trucks: List[Truck],
                        delivery_points: List[DeliveryPoint],
                        optimized_routes: List[OptimizedRoute]) -> None:
        """Add route lines to the map."""
        truck_dict = {truck.id: truck for truck in trucks}
        
        for i, route in enumerate(optimized_routes):
            if not route.route:
                continue
            
            truck = truck_dict.get(route.truck_id)
            if not truck:
                continue
            
            color = self.colors[i % len(self.colors)]
            
            # Create route coordinates
            route_coords = [truck.start]  # Start from truck position
            
            for point_idx in route.route:
                if point_idx < len(delivery_points):
                    route_coords.append(delivery_points[point_idx].location)
            
            # Add route line
            if len(route_coords) > 1:
                # Try to get detailed route geometry if router is available
                if self.router:
                    self._add_detailed_route(m, route_coords, color, route.truck_id)
                else:
                    self._add_simple_route(m, route_coords, color, route.truck_id)
    
    def _add_detailed_route(self, m: folium.Map, route_coords: List[List[float]], 
                          color: str, truck_id: int) -> None:
        """Add detailed route using actual road network."""
        try:
            # Get route segments with actual geometry
            full_route = []
            
            for i in range(len(route_coords) - 1):
                start = route_coords[i]
                end = route_coords[i + 1]
                
                # Get route geometry from router
                geometry = self.router.get_route_geometry(start, end)
                
                if geometry and isinstance(geometry, list):
                    # Add geometry points (convert from [lon, lat] to [lat, lon])
                    for coord in geometry:
                        if isinstance(coord, list) and len(coord) >= 2:
                            full_route.append([coord[1], coord[0]])
                else:
                    # Fallback to straight line
                    full_route.extend([start, end])
            
            if full_route:
                folium.PolyLine(
                    locations=full_route,
                    color=color,
                    weight=4,
                    opacity=0.8,
                    popup=f"Truck {truck_id} Route"
                ).add_to(m)
            
        except Exception as e:
            print(f"Failed to get detailed route geometry: {e}")
            # Fallback to simple route
            self._add_simple_route(m, route_coords, color, truck_id)
    
    def _add_simple_route(self, m: folium.Map, route_coords: List[List[float]], 
                         color: str, truck_id: int) -> None:
        """Add simple straight-line route."""
        folium.PolyLine(
            locations=route_coords,
            color=color,
            weight=4,
            opacity=0.8,
            popup=f"Truck {truck_id} Route",
            tooltip=f"Truck {truck_id}"
        ).add_to(m)
        
        # Add arrows to show direction
        for i in range(len(route_coords) - 1):
            start = route_coords[i]
            end = route_coords[i + 1]
            
            # Calculate midpoint
            mid_lat = (start[0] + end[0]) / 2
            mid_lon = (start[1] + end[1]) / 2
            
            # Add direction arrow
            folium.Marker(
                location=[mid_lat, mid_lon],
                icon=folium.DivIcon(
                    html=f'<div style="color: {color}; font-size: 16px;">➤</div>',
                    icon_size=(20, 20),
                    icon_anchor=(10, 10)
                )
            ).add_to(m)
    
    def _add_legend(self, m: folium.Map, optimized_routes: List[OptimizedRoute]) -> None:
        """Add a legend to the map."""
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p><b>Route Legend</b></p>
        '''
        
        for i, route in enumerate(optimized_routes):
            color = self.colors[i % len(self.colors)]
            legend_html += f'''
            <p><span style="color: {color}; font-size: 20px;">●</span> 
               Truck {route.truck_id} ({len(route.route)} deliveries)</p>
            '''
        
        legend_html += '''
        <p><i class="fa fa-truck" style="color: red;"></i> Truck Start</p>
        <p><i class="fa fa-package" style="color: green;"></i> Low Priority</p>
        <p><i class="fa fa-package" style="color: orange;"></i> Medium Priority</p>
        <p><i class="fa fa-package" style="color: red;"></i> High Priority</p>
        </div>
        '''
        
        m.get_root().html.add_child(folium.Element(legend_html))
    
    def save_map(self, map_obj: folium.Map, filename: str) -> None:
        """Save map to HTML file."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        map_obj.save(filename)
        print(f"Map saved to: {filename}")
    
    def create_comparison_map(self,
                            trucks: List[Truck],
                            delivery_points: List[DeliveryPoint],
                            original_routes: List[OptimizedRoute],
                            updated_routes: Dict[int, List[int]],
                            failed_truck_id: int) -> folium.Map:
        """
        Create a map comparing original routes with updated routes after reassignment.
        
        Args:
            trucks: List of truck objects
            delivery_points: List of delivery point objects
            original_routes: Original optimized routes
            updated_routes: Updated routes after reassignment
            failed_truck_id: ID of the failed truck
            
        Returns:
            Folium map showing before/after comparison
        """
        center = self._calculate_map_center(trucks, delivery_points)
        m = folium.Map(location=center, zoom_start=12)
        
        # Add truck markers
        self._add_truck_markers(m, trucks)
        
        # Add delivery points
        self._add_delivery_markers(m, delivery_points)
        
        # Add original routes (dashed lines)
        truck_dict = {truck.id: truck for truck in trucks}
        
        for i, route in enumerate(original_routes):
            if route.truck_id == failed_truck_id:
                continue  # Skip failed truck
            
            truck = truck_dict.get(route.truck_id)
            if not truck or not route.route:
                continue
            
            color = self.colors[i % len(self.colors)]
            route_coords = [truck.start]
            
            for point_idx in route.route:
                if point_idx < len(delivery_points):
                    route_coords.append(delivery_points[point_idx].location)
            
            # Original route (dashed)
            if len(route_coords) > 1:
                folium.PolyLine(
                    locations=route_coords,
                    color=color,
                    weight=2,
                    opacity=0.5,
                    dash_array='10,10',
                    popup=f"Original Truck {route.truck_id} Route"
                ).add_to(m)
        
        # Add updated routes (solid lines)
        for truck_id, route_indices in updated_routes.items():
            truck = truck_dict.get(truck_id)
            if not truck or not route_indices:
                continue
            
            color = self.colors[truck_id % len(self.colors)]
            route_coords = [truck.start]
            
            for point_idx in route_indices:
                if point_idx < len(delivery_points):
                    route_coords.append(delivery_points[point_idx].location)
            
            # Updated route (solid)
            if len(route_coords) > 1:
                folium.PolyLine(
                    locations=route_coords,
                    color=color,
                    weight=4,
                    opacity=0.8,
                    popup=f"Updated Truck {truck_id} Route"
                ).add_to(m)
        
        # Add failed truck marker with special icon
        failed_truck = truck_dict.get(failed_truck_id)
        if failed_truck:
            folium.Marker(
                location=failed_truck.start,
                popup=f"Failed Truck {failed_truck_id}",
                icon=folium.Icon(color='black', icon='times', prefix='fa')
            ).add_to(m)
        
        return m
    
    def generate_route_summary_html(self,
                                  trucks: List[Truck],
                                  delivery_points: List[DeliveryPoint],
                                  optimized_routes: List[OptimizedRoute],
                                  etas: Optional[Dict[str, List[ETAInfo]]] = None) -> str:
        """Generate HTML summary of routes."""
        html = """
        <html>
        <head>
            <title>Route Optimization Summary</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .truck-section { margin-bottom: 30px; border: 1px solid #ccc; padding: 15px; }
                .truck-header { background-color: #f0f0f0; padding: 10px; margin: -15px -15px 15px -15px; }
                .delivery-list { list-style-type: none; padding: 0; }
                .delivery-item { margin: 5px 0; padding: 5px; background-color: #f9f9f9; }
                .summary-stats { background-color: #e6f3ff; padding: 15px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
        """
        
        # Summary statistics
        total_deliveries = sum(len(route.route) for route in optimized_routes)
        total_distance = sum(route.total_distance_m for route in optimized_routes)
        total_time = sum(route.total_time_s for route in optimized_routes)
        
        html += f"""
        <div class="summary-stats">
            <h2>Optimization Summary</h2>
            <p><strong>Total Deliveries:</strong> {total_deliveries}</p>
            <p><strong>Total Distance:</strong> {total_distance/1000:.1f} km</p>
            <p><strong>Total Time:</strong> {total_time/3600:.1f} hours</p>
            <p><strong>Trucks Used:</strong> {len(optimized_routes)} of {len(trucks)}</p>
        </div>
        """
        
        # Individual truck routes
        truck_dict = {truck.id: truck for truck in trucks}
        
        for route in optimized_routes:
            truck = truck_dict.get(route.truck_id)
            if not truck:
                continue
            
            html += f"""
            <div class="truck-section">
                <div class="truck-header">
                    <h3>Truck {truck.id}</h3>
                    <p>Capacity: {truck.capacity} | Speed: {truck.speed_kmh} km/h</p>
                    <p>Route Distance: {route.total_distance_m/1000:.1f} km | 
                       Time: {route.total_time_s/3600:.1f} hours | 
                       Deliveries: {len(route.route)}</p>
                </div>
                <ul class="delivery-list">
            """
            
            for i, point_idx in enumerate(route.route):
                if point_idx < len(delivery_points):
                    point = delivery_points[point_idx]
                    
                    # Get ETA if available
                    eta_text = ""
                    if etas and str(route.truck_id) in etas:
                        truck_etas = etas[str(route.truck_id)]
                        if i < len(truck_etas):
                            eta = truck_etas[i]
                            eta_text = f" | ETA: {eta.eta}"
                    
                    html += f"""
                    <li class="delivery-item">
                        {i+1}. Point {point.id} - Demand: {point.demand} | 
                        Window: {point.time_window_start}-{point.time_window_end}{eta_text}
                    </li>
                    """
            
            html += "</ul></div>"
        
        html += "</body></html>"
        return html


if __name__ == "__main__":
    # Example usage
    from data_loader import DataLoader
    from optimizer import RouteOptimizer
    from eta_calculator import ETACalculator
    from router import Router
    
    # Generate sample data
    loader = DataLoader()
    trucks, deliveries = loader.generate_sample_data(num_trucks=3, num_deliveries=10)
    
    # Create components
    router = Router()
    optimizer = RouteOptimizer(router)
    eta_calculator = ETACalculator(router)
    visualizer = RouteVisualizer(router)
    
    try:
        # Optimize routes
        routes = optimizer.optimize_routes(trucks, deliveries)
        
        # Calculate ETAs
        etas = eta_calculator.calculate_route_etas(trucks, deliveries, routes)
        
        # Create visualization
        route_map = visualizer.create_route_map(trucks, deliveries, routes, etas)
        
        # Save map
        os.makedirs("output", exist_ok=True)
        visualizer.save_map(route_map, "output/route_map.html")
        
        # Generate summary
        summary_html = visualizer.generate_route_summary_html(trucks, deliveries, routes, etas)
        with open("output/route_summary.html", 'w', encoding='utf-8') as f:
            f.write(summary_html)
        
        print("Visualization complete! Check output/route_map.html")
        
    except Exception as e:
        print(f"Visualization failed: {e}")
